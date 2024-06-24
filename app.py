from flask import Flask, render_template, url_for, request, redirect, flash, session
from flask_mysqldb import MySQL
from flask_apscheduler import APScheduler
from datetime import datetime
from functools import wraps
from forms import LoginForm, AddBookForm, SearchBooksForm, DeleteForm, AddMemberForm, IssueBookForm, ReturnBookForm, CSRFForm
from helpers import authenticate_user, fetch_books_from_api, pick_valid_pairs_from_dict, prefill_form_values,get_new_available_count,cal_total_renting_cost_per_member,calculate_renting_cost_for_books, transform_form_data
from db_functions import add_new_record, get_all_records, get_record, edit_record, delete_record, search_string_in_table, get_rented_book_data, get_completed_transactions, update_book_count, get_books_issued_by_member, reduce_outstanding_debt
import app_secrets

#app config
app = Flask(__name__)
app.config['SECRET_KEY'] = app_secrets.FLASK_SECRET_KEY
app.config['MYSQL_HOST'] = app_secrets.MYSQL_HOST
app.config['MYSQL_USER'] = app_secrets.MYSQL_USER
app.config['MYSQL_PASSWORD'] = app_secrets.MYSQL_PASSWORD
app.config['MYSQL_PORT'] = app_secrets.MYSQL_PORT
app.config['MYSQL_DB'] = app_secrets.MYSQL_DB
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
#scheduler config 
scheduler = APScheduler()
scheduler.api_enabled = True
scheduler.init_app(app)
mysql = MySQL(app)
#scheduler to update outstanding debt, becuase it increases with the number of days the books are rented for
@scheduler.task('interval',id='update_outstanding_debt',seconds=100000)
def update_oustanding_debt():
    print("scheduler started")
    with scheduler.app.app_context():
        #Get data to calculate outstanding debt of members
        rented_books = get_rented_book_data(mysql.connection)
        #calculate outstanding debt
        cost_per_member = cal_total_renting_cost_per_member(rented_books)
        #update members with the latest outstanding debt
        for member_id in cost_per_member:
            success,error = edit_record(
                connection=mysql.connection,
                table_name='members',
                data_dict={'outstanding_debt':cost_per_member.get(member_id)},
                member_id=member_id
            )
            if error:
                print(error)

def login_required(f):
    @wraps(f)
    def wrapper(*args,**kwargs):
        if not session.get('username'):
            return redirect(url_for('login'))
        else:
            return f(*args,**kwargs)
    return wrapper

@app.route('/')
def get_login_page():
    return redirect(url_for('login')) 

@app.route('/login', methods=['GET','POST'])
def login():
    login_form = LoginForm()
    if request.method=='POST' and login_form.validate_on_submit():
        if authenticate_user(login_form.username.data, login_form.password.data):
            session['username'] = login_form.username.data
            return redirect('books')
        else:
            flash('Wrong username or password','error')
    return render_template('login.html', login_form=login_form)

@app.route('/books', methods=['GET'])
@login_required
def books():
    search_string = request.args.get('search')
    if search_string:
        books_count, books = search_string_in_table(
            connection=mysql.connection,
            table_name='books',
            fetch_columns=('book_id','title','authors','publisher','total_count','rented_count','available_count','isbn'),
            search_string=search_string,
            search_columns=('title','authors','publisher','isbn')
        )
    else:
        books_count, books = get_all_records(
            connection=mysql.connection,
            table_name='books',
            columns=('book_id','title','authors','publisher','total_count','rented_count','available_count','isbn'),
            modified_date='DESC',
            created_date='DESC',
            title='ASC'
        )
    if books_count:
        issue_book_form = IssueBookForm()
        #populate issue book form with member details
        _,members = get_all_records(connection=mysql.connection,table_name='members',columns=('member_id','name'),name='ASC')
        issue_book_form.member_id.choices = [(member['member_id'],member['name']) for member in members]
        issue_book_form.member_id.choices.insert(0,('',''))
        return render_template('books.html',books=books,issue_book_form=issue_book_form,search=search_string)
    else:
        if search_string:
            no_books_message = "No books were found for that search string."
        else:
            no_books_message = "There are no books added yet. Add or import new books to show up here."
        return render_template('books.html',search=search_string,no_books_message=no_books_message) 

@app.route('/addbook', methods=['GET', 'POST'])
@login_required
def add_book():
    add_book_form = AddBookForm()
    if request.method=='POST' and add_book_form.validate_on_submit():
        success, error = add_new_record(
            connection=mysql.connection,
            table_name='books',
            data_dict={'title':add_book_form.title.data,
                       'authors':add_book_form.authors.data,
                       'isbn':add_book_form.isbn.data,
                       'isbn13':add_book_form.isbn13.data,
                       'language_code':add_book_form.language_code.data,
                       'num_of_pages':add_book_form.num_of_pages.data,
                       'publisher':add_book_form.publisher.data,
                       'publication_date':add_book_form.publication_date.data,
                       'total_count':add_book_form.total_count.data,
                       'available_count': add_book_form.total_count.data, #available count is same as total count when the book is newly added
                       'ratings_count':add_book_form.ratings_count.data,
                       'text_reviews_count':add_book_form.text_reviews_count.data,
                       'average_rating':add_book_form.average_rating.data,
                       'renting_cost':add_book_form.renting_cost.data
                       }) 
        if success:
            flash("The book was added",'success')
        else:
            flash(f'The book could not be added becuase of the error {error}','error')
        return redirect(url_for('books'))
    else:
        return render_template('add_book.html', add_book_form=add_book_form)

@app.route('/search_books_to_import', methods=['GET','POST'])
@login_required
def search_to_import():
    search_books_form = SearchBooksForm()
    if request.method =='POST' and search_books_form.validate_on_submit():
        params_for_api = pick_valid_pairs_from_dict(search_books_form.data,('title','authors','isbn','publisher'))
        return redirect(url_for('import_books', **params_for_api))
    else:
        return render_template('search_to_import.html', search_books_form=search_books_form)

@app.route('/import_books',methods=['GET','POST'])
@login_required
def import_books():
    #get full details from frappe api for each book
    books = fetch_books_from_api(request.args)
    if books:
        csrf_form = CSRFForm()
        if request.method=='POST' and csrf_form.validate_on_submit():
            #get count and renting_cost of each book
            form_data = transform_form_data(request.form)
            #get full details from api response for each book
            books_to_import = [ book for book in books if book['isbn'] in form_data ]
            #add books to the database
            for book in books_to_import:     
                success, error = add_new_record(
                    connection=mysql.connection,
                    table_name='books',
                    data_dict={'title':book["title"],
                            'authors':book["authors"],
                            'isbn':book["isbn"],
                            'isbn13':book["isbn13"],
                            'language_code':book["language_code"],
                            'num_of_pages':book["  num_pages"],
                            'publisher':book["publisher"],
                            'publication_date':datetime.strptime(book["publication_date"],'%m/%d/%Y'),
                            'total_count':form_data.get(book["isbn"]).get('count'),
                            'available_count': form_data.get(book["isbn"]).get('count'), #available count is same as total count when the book is newly added
                            'ratings_count':book["ratings_count"],
                            'text_reviews_count':book["text_reviews_count"],
                            'average_rating':book["average_rating"],
                            'renting_cost':form_data.get(book["isbn"]).get('rent')
                            })
                if success:
                    continue
                else:
                    flash(f'Import could not be performed, following error occured {error}','error')
                    break                
            flash('The books were successfully imported','success')
            return redirect(url_for('books'))
        return render_template('import_books.html', books=books, csrf_form=csrf_form)
    else:
        no_books_message = "No books were found for that search."
        return render_template('import_books.html',no_books_message=no_books_message)
    
@app.route('/book/<string:book_id>', methods=['GET'])
@login_required
def view_book_details(book_id):
    book_details = get_record(
        connection=mysql.connection,
        table_name='books',
        columns=('book_id','title','authors','isbn','isbn13','language_code','num_of_pages','publisher','publication_date','available_count','total_count','rented_count','ratings_count','text_reviews_count','average_rating','renting_cost'),
        isbn=book_id
    )   
    delete_book_form = prefill_form_values(DeleteForm(),{'id':book_id})
    return render_template('view_book_details.html', book_details=book_details, delete_book_form=delete_book_form) 

@app.route('/edit/<string:book_id>',methods=['GET','POST'])
@login_required
def edit_book(book_id):
    edit_book_form = AddBookForm() 
    #get book details
    book_details = get_record(
        connection=mysql.connection,
        table_name='books',
        columns=('book_id','title','authors','isbn','isbn13','language_code','num_of_pages','publisher','publication_date','available_count','total_count','ratings_count','text_reviews_count','average_rating','renting_cost'),
        isbn=book_id
    )   
    if request.method == 'POST' and edit_book_form.validate_on_submit():
        #calculate new available count
        new_available_count =  get_new_available_count(
            old_available_count=book_details['available_count'],
            new_total_count=edit_book_form['total_count'].data,
            old_total_count=book_details['total_count'])
        if new_available_count < 0:
            flash('Total cannot be less than rented count','error')
            return render_template('edit_book.html', edit_book_form=edit_book_form)
        else:
            success,error = edit_record(
                connection=mysql.connection,
                table_name='books',
                data_dict={
                    'title': edit_book_form.title.data,
                    'authors':edit_book_form.authors.data,
                    'isbn': edit_book_form.isbn.data,
                    'isbn13': edit_book_form.isbn13.data,
                    'language_code': edit_book_form.language_code.data,
                    'num_of_pages': edit_book_form.num_of_pages.data,
                    'publisher': edit_book_form.publisher.data,
                    'publication_date': edit_book_form.publication_date.data,
                    'total_count': edit_book_form.total_count.data,
                    'available_count': new_available_count,
                    'ratings_count': edit_book_form.ratings_count.data,
                    'text_reviews_count': edit_book_form.text_reviews_count.data,
                    'average_rating': edit_book_form.average_rating.data,
                    'renting_cost':edit_book_form.renting_cost.data
                },
                book_id=book_details['book_id']
            )
            if success:
                flash('Book edited successfully','success')
                return redirect(url_for('books'))
            else:
                flash(f'Book could not be edited, following error occured {error}','error')
    edit_book_form = prefill_form_values(edit_book_form,book_details)
    return render_template('edit_book.html',edit_book_form=edit_book_form)

@app.route('/delete_book', methods=['POST'])
@login_required
def delete_book():
    delete_book_form = DeleteForm()
    if delete_book_form.validate_on_submit():
        success, error = delete_record(
            connection=mysql.connection,
            table_name='books',
            isbn=delete_book_form.id.data
        )
        if success:
            flash('Book Deleted Successfully','success')
        else:
            flash(f"Book could not be deleted, following error occured {error}","error")
        return redirect(url_for('books'))

@app.route('/members')
@login_required
def members():
    search_string = request.args.get('search')
    if search_string:
        member_count,members = search_string_in_table(
            connection=mysql.connection,
            table_name='members',
            fetch_columns=('member_id','name','email','created_date','outstanding_debt'),
            search_string=search_string,
            search_columns=('name','email')
        )
    else:
        member_count,members = get_all_records(
            connection=mysql.connection,
            table_name='members',
            columns=('member_id','name','email','created_date','outstanding_debt'),
            modified_date='DESC',
            created_date='DESC',
            name='ASC'
        )
    if member_count:
        delete_member_form = DeleteForm()
        return render_template('members.html',members=members, delete_member_form=delete_member_form,search=search_string)
    else:
        if search_string:
            no_members_message = "No members were found for that search."
        else:
            no_members_message = "There are no members added yet. Add new members to show up here."
        return render_template('members.html',search=search_string,no_members_message=no_members_message)

@app.route('/add_member',methods=['GET','POST'])
@login_required
def add_member():
    add_member_form = AddMemberForm()
    if request.method=='POST' and add_member_form.validate_on_submit():
        success,error = add_new_record(
            connection=mysql.connection,
            table_name='members',
            data_dict={
                'name':add_member_form.name.data,
                'email':add_member_form.email.data
            }
            )
        if success:
            flash("Member was added",'success')
            return redirect(url_for('members'))
        else:
            flash(f"Member could not be added, following error occured {error}","error")
    return render_template('add_member.html',add_member_form=add_member_form)

@app.route('/edit_member/<string:member_email>',methods=['GET','POST'])
@login_required
def edit_member(member_email):
    edit_member_form = AddMemberForm()
    member_details = get_record(connection=mysql.connection,table_name='members',columns=('member_id','name','email'), email=member_email)
    if request.method == 'POST' and edit_member_form.validate_on_submit():
        success, error = edit_record(
            connection=mysql.connection,
            table_name='members',
            data_dict={'name':edit_member_form.name.data, 'email':edit_member_form.email.data},
            member_id=member_details['member_id']
        )
        if success:
            flash("Member details edited successfully", 'success')
            return redirect(url_for('members'))
        else:
            flash(f"Member details could not be edited, following error occured {error}","error")    
    edit_member_form = prefill_form_values(edit_member_form,member_details)
    return render_template('edit_member.html',edit_member_form=edit_member_form)

@app.route('/delete_member',methods=['POST'])
@login_required
def delete_member():
    delete_member_form = DeleteForm()
    if delete_member_form.validate_on_submit():
        success,error = delete_record(
            connection=mysql.connection,
            table_name='members',
            email=delete_member_form.id.data
        )
        if success:
            flash("Member deleted successfully",'success')
        else:
            flash(f"Member could not be deleted, following error occured {error}","error")
        return redirect(url_for('members'))

@app.route('/transactions',methods=['GET'])
@login_required
def transactions():
    transactions = get_completed_transactions(mysql.connection)
    return render_template('transactions.html',transactions=transactions)

@app.route('/issue_book',methods=['POST'])
@login_required
def issue_book():
    issue_book_form=IssueBookForm()
    if issue_book_form.validate_on_submit():
        #get member's oustanding debt
        members_outstanding_debt = get_record(connection=mysql.connection,table_name='members',columns=('outstanding_debt',),member_id=issue_book_form.member_id.data)['outstanding_debt']
        #issue book if debt is less than 500
        if members_outstanding_debt <= 500:
            success, error = add_new_record(connection=mysql.connection,table_name='transactions',data_dict={
                    'book_id':issue_book_form.book_id.data,
                    'member_id':issue_book_form.member_id.data            
                }
            )
            #update books table for rented and available count
            success, error = update_book_count(connection=mysql.connection,book_id=issue_book_form.book_id.data,action='issue')
            if success:
                flash("Book was issued","success")
            else:
                flash(f"Book could not be issued, following error occured {error}",'error')
        else:
            flash("Member's outstanding debt is more than 500","error")
        return redirect(url_for('books'))
    
def return_books_from_member(books_issued_by_member,returned_book_ids,member_id,total_amount_paid_by_member):
    for book_id in returned_book_ids:
        #get renting cost of the book being returned
        total_renting_cost = [ book.get('total_renting_cost') for book in books_issued_by_member if book['book_id']==book_id][0]
        #update transactions table
        success, error = edit_record(
            connection=mysql.connection,
            table_name='transactions',
            data_dict={
                'returned_on':datetime.now(),
                'amount_paid':total_renting_cost,
            },
            book_id=book_id,
            member_id=member_id)
        if success:
            #update available and rented counts
            success,error = update_book_count(connection=mysql.connection,book_id=book_id,action='return')
            if success:
                continue
            else:
                return (success,error)    
        else:
            return (success,error)     
    #reduce member' outstanding debt by the amount paid
    success,error = reduce_outstanding_debt(connection=mysql.connection,member_id=member_id,reduce_by=total_amount_paid_by_member)
    return (success,error)

@app.route('/return/from/<int:member_id>',methods=['GET','POST'])
@login_required
def return_book(member_id):
    return_book_form = ReturnBookForm()
    #get books issued by member
    books_issued_by_member = get_books_issued_by_member(connection=mysql.connection,member_id=member_id)
    if books_issued_by_member:
        #calculate renting cost of all books issued by member
        books_issued_by_member = calculate_renting_cost_for_books(books_issued_by_member)
        #populate return book form with values
        return_book_form.return_book.choices = [ (book['book_id'],book['title']) for book in books_issued_by_member ]
        if request.method =='POST' and return_book_form.validate_on_submit():
            success,error = return_books_from_member(
                books_issued_by_member=books_issued_by_member,
                returned_book_ids=return_book_form.return_book.data,
                member_id=member_id,
                total_amount_paid_by_member=return_book_form.total_amount_paid.data
            )
            if success:
                flash('Book(s) returned successfully','success')
            else:
                flash(f'Book(s) could not be returned, following error occured {error}','error')
            return redirect(url_for('members'))
        return render_template('return_book.html',return_book_form=return_book_form,books=books_issued_by_member)
    else:
        flash("This member has no issued books",'error')
        return redirect(url_for('members'))

@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__=="__main__":
    scheduler.start()
    app.run(host="0.0.0.0",port=5000,debug=True)


