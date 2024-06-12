from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField, IntegerField, FloatField, HiddenField, EmailField, SelectField,SelectMultipleField,widgets, FieldList, FormField
from wtforms.validators import InputRequired, Length, NumberRange

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[ InputRequired(), Length(min=2,max=20)])
    password = PasswordField('Password', validators=[ InputRequired(), Length(min=2,max=20)])
    submit = SubmitField('Login')

class AddBookForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired(), Length(min=2,max=265)])
    authors = StringField('Author', validators=[InputRequired(), Length(min=2,max=150)])
    isbn = StringField('ISBN',validators=[InputRequired(), Length(min=10,max=10)])
    isbn13 = StringField('ISBN 13',validators=[InputRequired(), Length(min=13,max=13)])
    publisher = StringField('Publisher',validators=[InputRequired(), Length(min=2,max=265)])
    publication_date = DateField('Publication Date',validators=[InputRequired()])
    num_of_pages = IntegerField('No. of pages', validators=[InputRequired()])
    language_code = StringField('Language Code', validators=[InputRequired(), Length(min=2,max=10)])
    ratings_count = IntegerField('No. of ratings')      
    text_reviews_count = IntegerField('No. of text reviews')
    average_rating = FloatField('Average rating')
    total_count = IntegerField('Count of books', validators=[InputRequired()])
    renting_cost = IntegerField('Renting cost (per day)',validators=[InputRequired(),NumberRange(min=0,max=1000)])

class SearchBooksForm(FlaskForm):
    title = StringField('Title', validators=[Length(min=0,max=265)])
    authors = StringField('Author', validators=[Length(min=0,max=150)])
    isbn = StringField('ISBN',validators=[Length(min=0,max=10)])
    publisher = StringField('Publisher',validators=[Length(min=0,max=265)])

class DeleteForm(FlaskForm):
    id = HiddenField()

class AddMemberForm(FlaskForm):
    name = StringField('Name',validators=[InputRequired(),Length(min=2,max=256)])
    email = EmailField('Email',validators=[InputRequired()])

class IssueBookForm(FlaskForm):
    book_id = HiddenField(validators=[InputRequired()])
    member_id = SelectField('Issue to Member',validators=[InputRequired()],validate_choice=False)

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class ReturnBookForm(FlaskForm):
    return_book = MultiCheckboxField('',validate_choice=False,coerce=int)
    total_amount_paid = HiddenField()

class CSRFForm(FlaskForm):
    pass

class SelectBookForm(FlaskForm):
    book_id = HiddenField()
    book_count = IntegerField()

class ImportBooksForm(FlaskForm):
    books = FieldList(FormField(SelectBookForm),min_entries=1)