# Copyright (c) 2023, jay and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns, data = [], []
	columns, data = get_columns(filters), get_data(filters)
     
	return columns, data


def get_columns(filters):
    columns = [
        {
            'label':'Posting Date',
            'fieldname':"posting_date",
            'fieldtype':"Date",
            'width': 90
        },
        {
            'label':'Invoice No',
            'fieldname':"name",
            'fieldtype':"Link",
            'options':"Sales Invoice",
            'width': 150
        },
        {
            'label':'Customer LPO',
            'fieldname':"po_no",
            'fieldtype':"Data",
            'width': 90
        },
        {
            'label':'Due Date',
            'fieldname':"due_date",
            'fieldtype':"Date",
            'width': 90
        },

       {
            'label':'Grand Total',
            'fieldname':"grand_total",
            'fieldtype':"Currency",
            'width': 120
        },
       {
            'label':'Paid Amount',
            'fieldname':"paid_amount",
            'fieldtype':"Currency",
            'width': 120
        },
       {
            'label':'Outstanding Amount',
            'fieldname':"outstanding_amount",
            'fieldtype':"Currency",
            'width': 120
        },
        {
            'label':'Age (Days)',
            'fieldname':"age_days",
            'fieldtype':"Data",
            'width': 120
        },

    ]
    return columns
    
def get_data(filters):
	date_type = ""
	if filters.age_based_on == "Posting Date":
		date_type = 'posting_date'
	elif filters.age_based_on == "Due Date":
		date_type = 'due_date'

	data = frappe.db.sql('''
		SELECT name, po_no, customer, posting_date, due_date, grand_total, paid_amount, outstanding_amount, 
		CAST(DATEDIFF(NOW(), {0}) AS CHAR) AS age_days
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
		AND outstanding_amount > 0
		AND (customer = IFNULL(%(customer)s, "") OR %(customer)s IS NULL)
		AND {0} <= %(to_date)s
		ORDER BY {0};
		'''.format(date_type),
		{'from_date': filters.from_date, 'to_date': filters.to_date, 'customer': filters.customer}, as_dict=1)

	return data

