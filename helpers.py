import requests
from datetime import datetime


def authenticate_user(username,password):
    USERNAME='admin'
    PASSWORD='admin'
    if username==USERNAME and password==PASSWORD:
        return True
    else:
        return False
        
def fetch_books_from_api(params):
    BASE_URL = "https://frappe.io/api/method/frappe-library"
    books_response = requests.get(BASE_URL, params=params).json().get('message')
    return books_response
    
def pick_valid_pairs_from_dict(form_data_dict, keys_to_keep):
    dict_with_valid_pairs = { k:v for k,v in form_data_dict.items() if k in keys_to_keep and v}
    return dict_with_valid_pairs 

def prefill_form_values(form,details_dict):
    for field in form.data:
        if field !='csrf_token':
            form[field].data = details_dict[field]
    return form

def get_new_available_count(old_available_count,old_total_count,new_total_count):
    new_available_count = old_available_count + (new_total_count - old_total_count)
    return new_available_count

def calculate_renting_cost_per_book(issued_on, today ,renting_cost_per_day):
    number_of_days_delta = today - issued_on
    total_cost = number_of_days_delta.days*renting_cost_per_day
    return total_cost

def calculate_renting_cost_for_books(books):
    for book in books:
        book['total_renting_cost'] = calculate_renting_cost_per_book(book['issued_on'],datetime.today(),book['renting_cost'])
    return books

def get_total_renting_cost_per_member(members):
    cost_per_member = {}
    for member in members:
        cost_per_member[member['member_id']] = member.get('total_renting_cost')+ cost_per_member.get(member['member_id'],0)
    return cost_per_member

def cal_total_renting_cost_per_member(rented_books):
    books_with_renting_cost = calculate_renting_cost_for_books(rented_books)
    cost_per_member = get_total_renting_cost_per_member(books_with_renting_cost)
    return cost_per_member

def transform_form_data(form_data):
    result = {}
    for key,value in form_data.items():
        if key!='csrf_token':
            isbn,field = key.split('_')
            if result.get(isbn):
                result[isbn][field] = value
            else:
                result[isbn] = {field:value}
    return result