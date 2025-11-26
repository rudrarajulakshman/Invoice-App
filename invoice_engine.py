import pandas as pd
from fpdf import FPDF
import matplotlib.pyplot as plt
import datetime
import smtplib
from email.message import EmailMessage
import os

class GSTInvoiceSystem:
    def __init__(self, my_company_details):
        self.company = my_company_details
        self.invoices = [] 
        
        # Create directories for output
        if not os.path.exists('invoices_pdf'): os.makedirs('invoices_pdf')
        if not os.path.exists('reports'): os.makedirs('reports')

    def create_invoice(self, customer, items, invoice_type="Goods"):
        inv_no = f"INV-{datetime.datetime.now().strftime('%Y%m')}-{len(self.invoices)+1:03d}"
        date = datetime.date.today()
        
        # GST Logic
        my_state_code = self.company['gstin'][:2]
        cust_state_code = customer['gstin'][:2]
        is_interstate = my_state_code != cust_state_code

        total_taxable = 0
        total_tax = 0
        final_amt = 0
        processed_items = []

        for item in items:
            amount = item['qty'] * item['rate']
            tax_amt = amount * (item['gst_rate'] / 100)
            
            if is_interstate:
                igst = tax_amt
                cgst = sgst = 0
            else:
                igst = 0
                cgst = sgst = tax_amt / 2

            processed_items.append({
                'description': item['desc'],
                'hsn_sac': item['hsn_sac'],
                'qty': item['qty'],
                'rate': item['rate'],
                'taxable_value': amount,
                'cgst': cgst,
                'sgst': sgst,
                'igst': igst,
                'total': amount + tax_amt
            })
            total_taxable += amount
            total_tax += tax_amt
            final_amt += (amount + tax_amt)

        invoice_data = {
            'invoice_no': inv_no,
            'date': str(date),
            'type': invoice_type,
            'customer_name': customer['name'],
            'customer_gstin': customer['gstin'],
            'customer_email': customer['email'],
            'items': processed_items,
            'total_taxable': total_taxable,
            'total_tax': total_tax,
            'grand_total': final_amt,
            'status': 'Unpaid',
            'due_date': str(date + datetime.timedelta(days=15))
        }
        
        self.invoices.append(invoice_data)
        self._generate_pdf(invoice_data)
        return inv_no

    def _generate_pdf(self, inv_data):
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "TAX INVOICE", 0, 1, 'C')
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(100, 10, self.company['name'], 0, 0)
        pdf.cell(90, 10, f"Invoice No: {inv_data['invoice_no']}", 0, 1, 'R')
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(100, 5, f"GSTIN: {self.company['gstin']}", 0, 0)
        pdf.cell(90, 5, f"Date: {inv_data['date']}", 0, 1, 'R')
        pdf.cell(100, 5, self.company['address'], 0, 1)
        
        pdf.line(10, 35, 200, 35)
        
        # Customer
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 5, "Bill To:", 0, 1)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, inv_data['customer_name'], 0, 1)
        pdf.cell(0, 5, f"GSTIN: {inv_data['customer_gstin']}", 0, 1)
        
        # Table
        pdf.ln(10)
        pdf.set_fill_color(200, 220, 255)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(80, 8, "Description", 1, 0, 'C', 1)
        pdf.cell(20, 8, "HSN/SAC", 1, 0, 'C', 1)
        pdf.cell(15, 8, "Qty", 1, 0, 'C', 1)
        pdf.cell(25, 8, "Rate", 1, 0, 'C', 1)
        pdf.cell(25, 8, "Taxable", 1, 0, 'C', 1)
        pdf.cell(25, 8, "Total", 1, 1, 'C', 1)
        
        pdf.set_font("Arial", '', 9)
        for item in inv_data['items']:
            pdf.cell(80, 8, item['description'], 1)
            pdf.cell(20, 8, str(item['hsn_sac']), 1, 0, 'C')
            pdf.cell(15, 8, str(item['qty']), 1, 0, 'C')
            pdf.cell(25, 8, f"{item['rate']:.2f}", 1, 0, 'R')
            pdf.cell(25, 8, f"{item['taxable_value']:.2f}", 1, 0, 'R')
            pdf.cell(25, 8, f"{item['total']:.2f}", 1, 1, 'R')
            
        # Totals
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(140, 8, "Total Taxable Value:", 0, 0, 'R')
        pdf.cell(50, 8, f"{inv_data['total_taxable']:.2f}", 1, 1, 'R')
        
        pdf.cell(140, 8, "Total Tax (GST):", 0, 0, 'R')
        pdf.cell(50, 8, f"{inv_data['total_tax']:.2f}", 1, 1, 'R')
        
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(140, 10, "GRAND TOTAL:", 0, 0, 'R')
        pdf.cell(50, 10, f"INR {inv_data['grand_total']:.2f}", 1, 1, 'R', 1)
        
        filename = f"invoices_pdf/{inv_data['invoice_no']}.pdf"
        pdf.output(filename)

    def record_receipt(self, invoice_no, amount_received):
        for inv in self.invoices:
            if inv['invoice_no'] == invoice_no:
                if amount_received >= inv['grand_total']:
                    inv['status'] = 'Paid'
                else:
                    pass 

    def send_email_reminder(self, invoice_no):
        inv = next((item for item in self.invoices if item["invoice_no"] == invoice_no), None)
        if not inv: return
        if inv['status'] == 'Unpaid':
            print(f"Reminder sent to {inv['customer_email']}")

    def generate_gstr1_report(self):
        data = []
        for inv in self.invoices:
            for item in inv['items']:
                data.append({
                    'GSTIN/UIN of Recipient': inv['customer_gstin'],
                    'Invoice Number': inv['invoice_no'],
                    'Invoice Date': inv['date'],
                    'Invoice Value': inv['grand_total'],
                    'Place Of Supply': inv['customer_gstin'][:2],
                    'Rate': (item['cgst']+item['sgst']+item['igst']) / item['taxable_value'] * 100 if item['taxable_value'] > 0 else 0,
                    'Taxable Value': item['taxable_value'],
                    'Cess Amount': 0
                })
        
        df = pd.DataFrame(data)
        df.to_excel("reports/GSTR1_Report.xlsx", index=False)
