# Shelflife

## About
A simple library management web application made with Flask, MySQL and Tailwind

## Setup
Make sure you have Python3+ and MySQL installed on your system. Clone or download this repository. Run following commands in the terminal from inside the repository.

1. Create a virtual environment
    ```sh
   python3 -m venv myenv
   ```
2. Activate the virtual environment
    ```sh
    source myenv/bin/activate
    ```
3. Install requirements
   ```sh
   pip install -r requirements.txt
   ```
4. Edit `app_secrets.py` and `setup_db.py` with your values

5. Run `setup_db.py`
    ```sh
    python3 setup_db.py
    ```
6. Run `app.py`
    ```sh
    python3 app.py
    ```

## Screenshots
#### Books
![books](/screenshots/books.png?raw=true "Books")
#### Add book
![add book](/screenshots/add_book.png?raw=true "Add Book")
#### Edit book
![edit book](/screenshots/edit_book.png?raw=true "Edit Book")
#### View book details
![view book](/screenshots/book_details.png?raw=true "View Book")
#### Import books using API
![search using api](/screenshots/search_using_api.png?raw=true "Search using API")
![import books](/screenshots/import_books.png?raw=true "Import Books")
#### Search books
![search book](/screenshots/search_book.png?raw=true "Search Book")
#### Members
![members](/screenshots/members.png?raw=true "Members")
#### Add member
![add member](/screenshots/add_member.png?raw=true "Add member")
#### Edit member
![edit member](/screenshots/edit_member.png?raw=true "Edit Member")
#### Confirm delete
![delete member](/screenshots/confirm_delete.png?raw=true "Delete Member")
#### Search member
![search member](/screenshots/search_member.png?raw=true "Search Member")
#### Issue book
![issue book](/screenshots/issue_book.png?raw=true "Issue book")
#### Return book
![return book](/screenshots/return_books.png?raw=true "Return Book")
#### Transactions
![transactions](/screenshots/transactions.png?raw=true "Transactions")