import itertools
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import cint


from hrms.hr.doctype.employee_checkin.employee_checkin import (
	calculate_working_hours,
	mark_attendance_and_link_log,
)

@frappe.whitelist()
def process_auto_attendance(self):
	
	if (
		not cint(self.enable_auto_attendance)
		or not self.process_attendance_after
		or not self.last_sync_of_checkin
	):
		return

	logs = self.get_employee_checkins()
	
	for key, group in itertools.groupby(logs, key=lambda x: (x["employee"], x["shift_start"])):
		single_shift_logs = list(group)
		attendance_date = single_shift_logs[0].shift_actual_start.date()
		employee = key[0]
		if not self.should_mark_attendance(employee, attendance_date):
			continue

		(
			attendance_status,
			working_hours,
			late_entry,
			early_exit,
			in_time,
			out_time,
		) = self.get_attendance(single_shift_logs)


		mark_attendance_and_link_log(
			single_shift_logs,
			attendance_status,
			attendance_date,
			working_hours,
			late_entry,
			early_exit,
			in_time,
			out_time,
			self.name,
		)

	for employee in self.get_assigned_employees(self.process_attendance_after, True):
		self.mark_absent_for_dates_with_no_attendance(employee)

def mark_attendance_and_link_log(
	logs,
	attendance_status,
	attendance_date,
	working_hours=None,
	late_entry=False,
	early_exit=False,
	in_time=None,
	out_time=None,
	shift=None,
):
	"""Creates an attendance and links the attendance to the Employee Checkin.
	Note: If attendance is already present for the given date, the logs are marked as skipped and no exception is thrown.

	:param logs: The List of 'Employee Checkin'.
	:param attendance_status: Attendance status to be marked. One of: (Present, Absent, Half Day, Skip). Note: 'On Leave' is not supported by this function.
	:param attendance_date: Date of the attendance to be created.
	:param working_hours: (optional)Number of working hours for the given date.
	"""
	
	log_names = [x.name for x in logs]
	employee = logs[0].employee

	if attendance_status == "Skip":
		skip_attendance_in_checkins(log_names)
		return None
	elif attendance_status in ("Present", "Absent", "Half Day"):
		try:
			frappe.db.savepoint("attendance_creation")
			attendance = frappe.new_doc("Attendance")
			attendance.update(
				{
					"doctype": "Attendance",
					"employee": employee,
					"attendance_date": attendance_date,
					"status": attendance_status,
					"working_hours": working_hours,
					"shift": shift,
					"late_entry": late_entry,
					"early_exit": early_exit,
					"in_time": in_time,
					"out_time": out_time,
				}
			)
			attendance.save() 
			get_overtime(attendance)
			attendance.save()

			# if attendance.custom_overtime_hours <= 0 :
			# 	attendance.submit()

				
			if attendance_status == "Absent":
				attendance.add_comment(
					text=_("Employee was marked Absent for not meeting the working hours threshold.")
				)

			update_attendance_in_checkins(log_names, attendance.name)
			return attendance

		except frappe.ValidationError as e:
			handle_attendance_exception(log_names, e)

	else:
		frappe.throw(_("{} is an invalid Attendance Status.").format(attendance_status))
		
def handle_attendance_exception(log_names: list, error_message: str):
	frappe.db.rollback(save_point="attendance_creation")
	frappe.clear_messages()
	skip_attendance_in_checkins(log_names)
	add_comment_in_checkins(log_names, error_message)

def add_comment_in_checkins(log_names: list, error_message: str):
	text = "{0}<br>{1}".format(frappe.bold(_("Reason for skipping auto attendance:")), error_message)

	for name in log_names:
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "Employee Checkin",
				"reference_name": name,
				"content": text,
			}
		).insert(ignore_permissions=True)


def skip_attendance_in_checkins(log_names: list):
	EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
	(
		frappe.qb.update(EmployeeCheckin)
		.set("skip_auto_attendance", 1)
		.where(EmployeeCheckin.name.isin(log_names))
	).run()


def update_attendance_in_checkins(log_names: list, attendance_id: str):
	EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
	(
		frappe.qb.update(EmployeeCheckin)
		.set("attendance", attendance_id)
		.where(EmployeeCheckin.name.isin(log_names))
	).run()

def get_overtime(doc):
	if doc.shift and doc.working_hours:
			
		shift = frappe.get_doc('Shift Type',doc.shift)

		normal_working_hours = frappe.utils.time_diff_in_hours( shift.end_time, shift.start_time)

		overtime_hours = round(doc.working_hours - normal_working_hours, 2)
		
		doc.custom_overtime_hours = overtime_hours
