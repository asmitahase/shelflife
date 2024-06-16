from flask import Flask, render_template, url_for, request, redirect, flash, session
from flask_mysqldb import MySQL
from flask_apscheduler import APScheduler
from datetime import datetime
from functools import wraps
from forms import LoginForm, AddBookForm, SearchBooksForm, DeleteForm, AddMemberForm, IssueBookForm, ReturnBookForm, CSRFForm, ImportBooksForm
from helpers import authenticate_user, fetch_books_from_api, pick_valid_pairs_from_dict, prefill_form_values,get_new_available_count,set_total_renting_cost_per_book,get_total_renting_cost_per_member
from db_functions import add_new_record, get_all_records, get_record, edit_record, delete_record, search_string_in_table
import app_secrets


app = Flask(__name__)
app.config['SECRET_KEY'] = app_secrets.FLASK_SECRET_KEY
app.config['MYSQL_HOST'] = app_secrets.MYSQL_HOST
app.config['MYSQL_USER'] = app_secrets.MYSQL_USER
app.config['MYSQL_PASSWORD'] = app_secrets.MYSQL_PASSWORD
# app.config['MYSQL_PORT'] = app_secrets.MYSQL_PORT
app.config['MYSQL_DB'] = app_secrets.MYSQL_DB
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

scheduler = APScheduler()
scheduler.api_enabled = True
scheduler.init_app(app)

mysql = MySQL(app)

@scheduler.task('interval',id='update_outstanding_debt',seconds=14400)
def update_oustanding_debt():
    print("scheduler started")
    with scheduler.app.app_context():
        #Get data to calculate outstanding debt of members
        cur = mysql.connection.cursor()
        cur.execute("SELECT books.book_id,books.renting_cost,transactions.issued_on,transactions.returned_on,members.member_id FROM books INNER JOIN transactions ON books.book_id=transactions.book_id INNER JOIN members ON transactions.member_id=members.member_id WHERE transactions.returned_on IS NULL")
        transactions = cur.fetchall()

        #calculate outstanding debt
        transactions = set_total_renting_cost_per_book(transactions)
        cost_per_member = get_total_renting_cost_per_member(transactions)

        #update members with the lastest oustading debt
        for member_id in cost_per_member:
            cur.execute("UPDATE members SET outstanding_debt=%s WHERE member_id=%s",[cost_per_member.get(member_id),member_id])
        mysql.connection.commit()
        cur.close()

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
    params_for_api = pick_valid_pairs_from_dict(request.args,('title','authors','isbn','publisher'))
    books = fetch_books_from_api(params_for_api)
    if books:
        csrf_form = CSRFForm()
        if request.method=='POST' and csrf_form.validate_on_submit():
            books_to_import = [ book for book in books if book['isbn'] in request.form ]
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
                            'total_count':request.form.get(book["isbn"]),
                            'available_count': request.form.get(book["isbn"]), #available count is same as total count when the book is newly added
                            'ratings_count':book["ratings_count"],
                            'text_reviews_count':book["text_reviews_count"],
                            'average_rating':book["average_rating"]
                            })
            if success:
                flash('The books were successfully imported','success')
            else:
                flash(f'Import could not be performed, following error occured {error}','error')
            return redirect(url_for('books'))
        return render_template('import_books.html', books=books, csrf_form=csrf_form)
    else:
        no_books_message = "No books were found for that search."
        return render_template('import_books.html',no_books_message=no_books_message)
@app.route('/view_book_details/<string:book_id>', methods=['GET'])
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

@app.route('/edit_book/<string:book_id>',methods=['GET','POST'])
@login_required
def edit_book(book_id):
    edit_book_form = AddBookForm() 
    book_details = get_record(
        connection=mysql.connection,
        table_name='books',
        columns=('book_id','title','authors','isbn','isbn13','language_code','num_of_pages','publisher','publication_date','available_count','total_count','ratings_count','text_reviews_count','average_rating','renting_cost'),
        isbn=book_id
    )   
    if request.method == 'POST' and edit_book_form.validate_on_submit():
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
    cur = mysql.connection.cursor()
    cur.execute("SELECT books.title,members.name,transactions.issued_on,transactions.returned_on,transactions.amount_paid FROM books INNER JOIN transactions ON books.book_id=transactions.book_id INNER JOIN members ON transactions.member_id=members.member_id WHERE returned_on IS NOT NULL ORDER BY transactions.returned_on DESC")
    transactions = cur.fetchall()
    return render_template('transactions.html',transactions=transactions)

@app.route('/issue_book',methods=['POST'])
@login_required
def issue_book():
    issue_book_form=IssueBookForm()
    if issue_book_form.validate_on_submit():
        member_details = get_record(connection=mysql.connection,table_name='members',columns=('outstanding_debt',),member_id=issue_book_form.member_id.data)
        if member_details['outstanding_debt'] <= 500:
            success, error = add_new_record(connection=mysql.connection,table_name='transactions',data_dict={
                    'book_id':issue_book_form.book_id.data,
                    'member_id':issue_book_form.member_id.data            
                }
            )
            #update books table for rented and available count
            cur = mysql.connection.cursor()
            cur.execute("UPDATE books SET available_count=available_count-1,rented_count=rented_count+1 WHERE book_id=%s",[issue_book_form.book_id.data])
            mysql.connection.commit()
            cur.close()
            flash("Book was issued","success")
        else:
            flash("Member's outstanding_debt is more than 500","error")
        return redirect(url_for('books'))
    

@app.route('/return_book/from/<int:member_id>',methods=['GET','POST'])
@login_required
def return_book(member_id):
    return_book_form = ReturnBookForm()
    cur = mysql.connection.cursor()
    count = cur.execute("SELECT books.book_id,books.title,books.renting_cost,transactions.issued_on FROM transactions INNER JOIN books ON transactions.book_id=books.book_id WHERE member_id=%s AND transactions.returned_on IS NULL",[member_id])
    books_issued_by_member = cur.fetchall()
    books_issued_by_member = set_total_renting_cost_per_book(books_issued_by_member)  
    return_book_form.return_book.choices = [ (book['book_id'],book['title']) for book in books_issued_by_member ]
    if request.method =='POST' and return_book_form.validate_on_submit():
        for book_id in return_book_form.return_book.data:
            #update transactions table with returned_on date and amount paid where bookid
            total_renting_cost = [ book.get('total_renting_cost') for book in books_issued_by_member if book['book_id']==book_id][0]
            cur.execute("UPDATE transactions SET returned_on=%s,amount_paid=%s WHERE book_id=%s AND member_id=%s",[
                datetime.now(),
                total_renting_cost,
                book_id,
                member_id
            ])
            #update books table with available and rented count where book_id
            cur.execute("UPDATE books SET available_count=available_count+1,rented_count=rented_count-1 WHERE book_id=%s",[book_id])

        #update memebers with outstanding debt where member_id
        cur.execute("UPDATE members SET outstanding_debt=outstanding_debt-%s WHERE member_id=%s",[return_book_form.total_amount_paid.data,member_id])
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('members'))
    cur.close()
    return render_template('return_book.html',return_book_form=return_book_form,books=books_issued_by_member)



@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))



if __name__=="__main__":
    scheduler.start()
    app.run(debug=True)


