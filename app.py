import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QLineEdit, QMessageBox, QDialog, QHBoxLayout, QCheckBox, QSpinBox, QHeaderView
)
from PyQt5.QtCore import Qt
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from twilio.rest import Client

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base

# Database setup
Base = declarative_base()
DATABASE_URL = 'sqlite:///students.db'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    contact = Column(String(15), nullable=False)
    last_paid_date = Column(DateTime, default=None)
    payment_duration = Column(Integer, default=1)  # Duration in months

# Check if the database exists before creating tables
if not os.path.exists('students.db'):
    Base.metadata.create_all(engine)
else:
    # Use Alembic or handle the schema change manually
    pass

# Twilio configuration
TWILIO_ACCOUNT_SID = 'your_account_sid'
TWILIO_AUTH_TOKEN = 'your_auth_token'
TWILIO_PHONE_NUMBER = 'your_twilio_phone_number'
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# GUI Application
class GymManagementApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gym Management System")
        self.setGeometry(100, 100, 800, 600)

        # Layouts
        layout = QVBoxLayout()

        # Add Student Section
        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("Enter Student Name")
        layout.addWidget(self.name_input)

        self.contact_input = QLineEdit(self)
        self.contact_input.setPlaceholderText("Enter Contact Number")
        layout.addWidget(self.contact_input)
        self.payment_duration_input = QSpinBox(self)
        self.payment_duration_input.setRange(1, 12)
        self.payment_duration_input.setValue(1)
        self.payment_duration_input.setSuffix(" months")
        layout.addWidget(self.payment_duration_input)


        add_button = QPushButton("Add Student")
        add_button.clicked.connect(self.add_student)
        layout.addWidget(add_button)

        # Unpaid Students Table
        self.unpaid_table = QTableWidget(self)
        self.unpaid_table.setColumnCount(5)
        self.unpaid_table.setHorizontalHeaderLabels(["ID", "Name", "Contact", "Duration (months)", "Last Paid Date"])
        layout.addWidget(self.unpaid_table)

        refresh_button = QPushButton("Refresh Unpaid Students")
        refresh_button.clicked.connect(self.refresh_unpaid_students)
        layout.addWidget(refresh_button)

        # Update Fees Button
        update_button = QPushButton("Mark Fees as Paid")
        update_button.clicked.connect(self.update_fees)
        layout.addWidget(update_button)

        # Send Reminder Button
        reminder_button = QPushButton("Send Reminders")
        reminder_button.clicked.connect(self.send_reminders)
        layout.addWidget(reminder_button)

        # View All Students Button
        view_button = QPushButton("View All Students")
        view_button.clicked.connect(self.view_all_students)
        layout.addWidget(view_button)

        # Edit Student Section
        edit_layout = QHBoxLayout()
        self.edit_id_input = QLineEdit(self)
        self.edit_id_input.setPlaceholderText("Enter Student ID to Edit")
        edit_layout.addWidget(self.edit_id_input)

        verify_button = QPushButton("Verify ID")
        verify_button.clicked.connect(self.verify_student_id)
        edit_layout.addWidget(verify_button)

        layout.addLayout(edit_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Load the unpaid students on startup
        self.refresh_unpaid_students()


    
    def add_student(self):
        name = self.name_input.text()
        contact = self.contact_input.text()
        payment_duration = self.payment_duration_input.value()

        if not name or not contact:
            QMessageBox.warning(self, "Input Error", "Please enter both name and contact.")
            return

        new_student = Student(
            name=name,
            contact=contact,
            last_paid_date=None,
            payment_duration=payment_duration
        )
        session.add(new_student)
        session.commit()
        QMessageBox.information(self, "Success", f"Student {name} added successfully!")

        # Clear the input fields
        self.name_input.setText("")
        self.contact_input.setText("")
        self.payment_duration_input.setValue(1)

        self.refresh_unpaid_students()


    def refresh_unpaid_students(self):
        current_date = datetime.now()
        students = session.query(Student).all()
        unpaid_students = []

        for student in students:
            # Check if the payment duration has expired
            if student.last_paid_date is None or (current_date - student.last_paid_date).days > (student.payment_duration * 30):
                unpaid_students.append(student)

        # Populate the unpaid students table
        self.unpaid_table.setRowCount(len(unpaid_students))
        
        for row, student in enumerate(unpaid_students):
            self.unpaid_table.setItem(row, 0, QTableWidgetItem(str(student.id)))
            self.unpaid_table.setItem(row, 1, QTableWidgetItem(student.name))
            self.unpaid_table.setItem(row, 2, QTableWidgetItem(student.contact))
            self.unpaid_table.setItem(row, 3, QTableWidgetItem(str(student.payment_duration)))

            # Last Paid Date column
            last_paid_date = student.last_paid_date.strftime("%Y-%m-%d") if student.last_paid_date else "Not Paid"
            self.unpaid_table.setItem(row, 4, QTableWidgetItem(last_paid_date))


    
    def update_fees(self):
        selected_row = self.unpaid_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Selection Error", "Please select a student from the table.")
            return

        student_id = int(self.unpaid_table.item(selected_row, 0).text())
        student = session.query(Student).get(student_id)
        student.last_paid_date = datetime.now()
        session.commit()
        QMessageBox.information(self, "Success", f"Fees marked as paid for {student.name}!")
        self.refresh_unpaid_students()

        
    def send_reminders(self):
        current_date = datetime.now()
        students = session.query(Student).all()
        unpaid_students = []

        for student in students:
            if student.last_paid_date is None or (current_date - student.last_paid_date).days > (student.payment_duration * 30):
                unpaid_students.append(student)

        for student in unpaid_students:
            message = f"Hello {student.name}, please pay your gym fees for this month."
            client.messages.create(
                body=message,
                from_=f'whatsapp:{TWILIO_PHONE_NUMBER}',
                to=f'whatsapp:{student.contact}'
            )
        QMessageBox.information(self, "Success", "Reminders sent to all unpaid students!")

    def view_all_students(self):
        self.view_window = ViewAllStudentsWindow()
        self.view_window.exec_()

    def verify_student_id(self):
        student_id = self.edit_id_input.text()

        if not student_id:
            QMessageBox.warning(self, "Input Error", "Please enter the student ID.")
            return

        student = session.query(Student).get(student_id)
        if not student:
            QMessageBox.warning(self, "Error", "Student not found.")
            return

        self.edit_window = EditStudentWindow(student)
        self.edit_window.exec_()

class EditStudentWindow(QDialog):
    def __init__(self, student):
        super().__init__()
        self.setWindowTitle("Edit Student Details")
        self.setGeometry(300, 300, 400, 200)
        self.student = student

        layout = QVBoxLayout()

        self.name_input = QLineEdit(self)
        self.name_input.setText(student.name)
        layout.addWidget(self.name_input)

        self.contact_input = QLineEdit(self)
        self.contact_input.setText(student.contact)
        layout.addWidget(self.contact_input)

        self.paid_checkbox = QCheckBox("Fees Paid")
        self.paid_checkbox.setChecked(student.last_paid_date is not None and student.last_paid_date.month == datetime.now().month and student.last_paid_date.year == datetime.now().year)
        layout.addWidget(self.paid_checkbox)

        save_button = QPushButton("Save Changes")
        save_button.clicked.connect(self.save_changes)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def save_changes(self):
        new_name = self.name_input.text()
        new_contact = self.contact_input.text()
        fees_paid = self.paid_checkbox.isChecked()

        if new_name:
            self.student.name = new_name
        if new_contact:
            self.student.contact = new_contact

        if fees_paid:
            self.student.last_paid_date = datetime.now()
        else:
            self.student.last_paid_date = None

        session.commit()
        QMessageBox.information(self, "Success", "Student details updated successfully!")
        self.close()

class ViewAllStudentsWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("All Students")
        self.setGeometry(200, 200, 600, 400)
        layout = QVBoxLayout()

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Contact", "Fees Paid", "Last Paid Date", "Payment Duration"])
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_students()

                     
    def load_students(self):
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive) 
        students = session.query(Student).all()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Contact", "Fees Paid", "Last Paid Date", "Payment Duration"])
        self.table.setRowCount(len(students))

        # Method 1: Resize columns to content
        self.table.resizeColumnsToContents()

        # Method 2: Set specific column widths
        # Adjust these values as needed
        self.table.setColumnWidth(0, 50)   # ID column
        self.table.setColumnWidth(1, 150)  # Name column
        self.table.setColumnWidth(2, 120)  # Contact column
        self.table.setColumnWidth(3, 80)   # Fees Paid column
        self.table.setColumnWidth(4, 120)  # Last Paid Date column
        self.table.setColumnWidth(5, 120)  # Payment Duration column

        # Method 3: Stretch last section to fill remaining space
        self.table.horizontalHeader().setStretchLastSection(True)

        # Optional: Enable word wrap for better readability
        self.table.setWordWrap(True)

        for row, student in enumerate(students):
            self.table.setItem(row, 0, QTableWidgetItem(str(student.id)))
            self.table.setItem(row, 1, QTableWidgetItem(student.name))
            self.table.setItem(row, 2, QTableWidgetItem(student.contact))
            
            fees_paid = "Yes" if student.last_paid_date and student.last_paid_date.month == datetime.now().month and student.last_paid_date.year == datetime.now().year else "No"
            self.table.setItem(row, 3, QTableWidgetItem(fees_paid))

            last_paid_date = student.last_paid_date.strftime("%Y-%m-%d") if student.last_paid_date else "Not Paid"
            self.table.setItem(row, 4, QTableWidgetItem(last_paid_date))

            self.table.setItem(row, 5, QTableWidgetItem(str(student.payment_duration)))
            

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GymManagementApp()
    window.show()
    sys.exit(app.exec_())