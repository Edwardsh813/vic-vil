#!/usr/bin/env python3
"""
Generate Ohio-Compliant Eviction Notices for Victorian Village Apartments.
Creates:
1. 3-Day Notice to Leave Premises (Nonpayment of Rent)
2. 30-Day Notice to Leave Premises (Lease Violation)
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def create_3day_notice():
    """Generate 3-Day Notice for Nonpayment of Rent (ORC § 5321.17)."""
    filename = os.path.join(OUTPUT_DIR, "3-day-notice-nonpayment.pdf")
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    left_margin = 0.75 * inch
    right_margin = width - 0.75 * inch
    top_margin = height - 0.75 * inch
    usable_width = right_margin - left_margin

    y = top_margin
    line_height = 14

    def center_text(text, size=14, bold=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawCentredString(width / 2, y, text)
        y -= size + 6

    def draw_text(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(left_margin + indent, y, text)
        y -= line_height

    def draw_wrapped(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        words = text.split()
        line = ""
        max_width = usable_width - indent

        for word in words:
            test = line + (" " if line else "") + word
            if c.stringWidth(test, font, size) <= max_width:
                line = test
            else:
                c.drawString(left_margin + indent, y, line)
                y -= line_height
                line = word
        if line:
            c.drawString(left_margin + indent, y, line)
            y -= line_height

    def space(lines=0.5):
        nonlocal y
        y -= line_height * lines

    # Header
    center_text("VICTORIAN VILLAGE APARTMENTS", size=14, bold=True)
    center_text("Jim and Jolinda Edwards, d/b/a Victorian Village Apartments", size=10)
    center_text("P.O. Box 471, Nelsonville, Ohio 45764 | 740-707-5851", size=10)
    space(1)

    center_text("THREE-DAY NOTICE TO LEAVE PREMISES", size=14, bold=True)
    center_text("(Nonpayment of Rent - Ohio Revised Code § 5321.17)", size=10)
    space(1)

    # Date
    draw_text("Date: _______________________")
    space(0.5)

    # Tenant info
    draw_text("TO:", bold=True)
    space(0.3)
    draw_text("Tenant Name(s): _________________________________________________________________")
    space(0.5)
    draw_text("Unit Address: _____________________________________________, Nelsonville, Ohio 45764")
    space(0.5)
    draw_text("Unit Number: _______________")
    space(1)

    # Notice text
    draw_text("NOTICE:", bold=True)
    space(0.3)
    draw_wrapped("You are hereby notified that you are in default of your lease agreement due to nonpayment of rent. The following amounts are due and owing:")
    space(0.7)

    # Amount owed section
    draw_text("Rent Due for Month of: _______________________     Amount: $_______________")
    space(0.5)
    draw_text("Rent Due for Month of: _______________________     Amount: $_______________")
    space(0.5)
    draw_text("Late Fee(s): $_______________")
    space(0.5)
    draw_text("Other Charges (describe): ____________________________     Amount: $_______________")
    space(0.5)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left_margin, y, "TOTAL AMOUNT DUE: $_______________")
    y -= line_height * 1.5

    space(0.5)

    # Demand - ORC § 5321.17(B) compliant language
    draw_wrapped("You have the option to prevent termination of this rental agreement by paying the total rent due on or before the date that is THREE (3) DAYS after service of this notice. The 3-day period begins the day after service is completed.")
    space(0.5)

    draw_wrapped("If you fail to pay the total amount due within three (3) days, your tenancy will terminate and you must vacate and surrender possession of the premises. The Landlord will then commence a forcible entry and detainer action pursuant to Ohio Revised Code § 1923.04 to recover possession of the premises, all rent due, late fees, court costs, and attorney's fees as permitted by law.")
    space(0.5)

    # Payment info
    draw_text("PAYMENT MAY BE MADE BY:", bold=True)
    space(0.3)
    draw_text("1. Innago online portal", indent=15)
    space(0.3)
    draw_text("2. Check mailed to P.O. Box 471, Nelsonville, Ohio 45764", indent=15)
    space(0.3)
    draw_text("3. Cash or check in rent drop box at 325 S. Harper St.", indent=15)
    space(1)

    # Legal notice
    draw_wrapped("This notice is given pursuant to Ohio Revised Code § 5321.17. This notice does not waive any rights of the Landlord, including the right to collect all amounts due under the lease agreement.")
    space(1)

    # Signature
    draw_text("_________________________________________          ___________________")
    draw_text("Landlord/Agent Signature                                              Date")
    space(0.5)
    draw_text("Print Name: ___________________________________")
    space(1.5)

    # Proof of service
    draw_text("PROOF OF SERVICE", bold=True)
    space(0.5)
    draw_text("I served this notice on the above-named tenant(s) on _____________________ (date)")
    space(0.5)
    draw_text("by the following method:")
    space(0.5)
    draw_text("___  Personal delivery to tenant", indent=15)
    space(0.4)
    draw_text("___  Personal delivery to adult resident at premises", indent=15)
    space(0.4)
    draw_text("___  Certified mail, return receipt requested", indent=15)
    space(1)
    draw_text("_________________________________________          ___________________")
    draw_text("Server Signature                                                           Date")

    c.save()
    print(f"Created: {filename}")
    return filename


def create_30day_notice():
    """Generate 30-Day Notice for Lease Violation (ORC § 5321.17)."""
    filename = os.path.join(OUTPUT_DIR, "30-day-notice-violation.pdf")
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    left_margin = 0.75 * inch
    right_margin = width - 0.75 * inch
    top_margin = height - 0.75 * inch
    usable_width = right_margin - left_margin

    y = top_margin
    line_height = 14

    def center_text(text, size=14, bold=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawCentredString(width / 2, y, text)
        y -= size + 6

    def draw_text(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(left_margin + indent, y, text)
        y -= line_height

    def draw_wrapped(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        words = text.split()
        line = ""
        max_width = usable_width - indent

        for word in words:
            test = line + (" " if line else "") + word
            if c.stringWidth(test, font, size) <= max_width:
                line = test
            else:
                c.drawString(left_margin + indent, y, line)
                y -= line_height
                line = word
        if line:
            c.drawString(left_margin + indent, y, line)
            y -= line_height

    def space(lines=0.5):
        nonlocal y
        y -= line_height * lines

    # Header
    center_text("VICTORIAN VILLAGE APARTMENTS", size=14, bold=True)
    center_text("Jim and Jolinda Edwards, d/b/a Victorian Village Apartments", size=10)
    center_text("P.O. Box 471, Nelsonville, Ohio 45764 | 740-707-5851", size=10)
    space(1)

    center_text("THIRTY-DAY NOTICE TO LEAVE PREMISES", size=14, bold=True)
    center_text("(Lease Violation - Ohio Revised Code § 5321.17)", size=10)
    space(1)

    # Date
    draw_text("Date: _______________________")
    space(0.5)

    # Tenant info
    draw_text("TO:", bold=True)
    space(0.3)
    draw_text("Tenant Name(s): _________________________________________________________________")
    space(0.5)
    draw_text("Unit Address: _____________________________________________, Nelsonville, Ohio 45764")
    space(0.5)
    draw_text("Unit Number: _______________")
    space(1)

    # Notice text
    draw_text("NOTICE:", bold=True)
    space(0.3)
    draw_wrapped("You are hereby notified that you are in MATERIAL NONCOMPLIANCE with your lease agreement pursuant to Ohio Revised Code § 5321.17(B). The specific violation(s) constituting material noncompliance are described below:")
    space(0.7)

    # Violation description box
    draw_text("DESCRIPTION OF VIOLATION(S):", bold=True)
    space(0.3)
    # Draw box for writing
    c.rect(left_margin, y - 80, usable_width, 85)
    y -= 95
    space(0.5)

    draw_text("Date(s) of Violation: _______________________________________________________")
    space(0.5)

    draw_text("Lease Section(s) Violated: __________________________________________________")
    space(1)

    # Demand - ORC § 5321.17(B) compliant language
    draw_wrapped("You have the option to prevent termination of this rental agreement by remedying the material noncompliance described above within THIRTY (30) DAYS of service of this notice.")
    space(0.5)

    draw_wrapped("If the material noncompliance is not remedied within thirty (30) days, your tenancy will terminate on the date specified below and you must vacate and surrender possession of the premises. The Landlord will then commence a forcible entry and detainer action pursuant to Ohio Revised Code § 1923.04 to recover possession of the premises, damages, court costs, and attorney's fees as permitted by law.")
    space(0.5)

    # Cure instructions
    draw_text("TO CURE THIS VIOLATION, YOU MUST:", bold=True)
    space(0.3)
    c.rect(left_margin, y - 50, usable_width, 55)
    y -= 65
    space(0.5)

    # Legal notice
    draw_wrapped("This notice is given pursuant to Ohio Revised Code § 5321.17. This notice does not waive any rights of the Landlord, including the right to pursue eviction for any subsequent violations.")
    space(0.5)

    draw_text("VACATE BY DATE (if not cured): _______________________", bold=True)
    space(1)

    # Signature
    draw_text("_________________________________________          ___________________")
    draw_text("Landlord/Agent Signature                                              Date")
    space(0.5)
    draw_text("Print Name: ___________________________________")
    space(1)

    # Proof of service
    draw_text("PROOF OF SERVICE", bold=True)
    space(0.5)
    draw_text("I served this notice on the above-named tenant(s) on _____________________ (date)")
    space(0.5)
    draw_text("by the following method:")
    space(0.5)
    draw_text("___  Personal delivery to tenant", indent=15)
    space(0.4)
    draw_text("___  Personal delivery to adult resident at premises", indent=15)
    space(0.4)
    draw_text("___  Certified mail, return receipt requested", indent=15)
    space(1)
    draw_text("_________________________________________          ___________________")
    draw_text("Server Signature                                                           Date")

    c.save()
    print(f"Created: {filename}")
    return filename


def create_nonrenewal_notice():
    """Generate Non-Renewal / Lease Termination Notice."""
    filename = os.path.join(OUTPUT_DIR, "notice-of-nonrenewal.pdf")
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    left_margin = 0.75 * inch
    right_margin = width - 0.75 * inch
    top_margin = height - 0.75 * inch
    usable_width = right_margin - left_margin

    y = top_margin
    line_height = 14

    def center_text(text, size=14, bold=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawCentredString(width / 2, y, text)
        y -= size + 6

    def draw_text(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(left_margin + indent, y, text)
        y -= line_height

    def draw_wrapped(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        words = text.split()
        line = ""
        max_width = usable_width - indent

        for word in words:
            test = line + (" " if line else "") + word
            if c.stringWidth(test, font, size) <= max_width:
                line = test
            else:
                c.drawString(left_margin + indent, y, line)
                y -= line_height
                line = word
        if line:
            c.drawString(left_margin + indent, y, line)
            y -= line_height

    def space(lines=0.5):
        nonlocal y
        y -= line_height * lines

    # Header
    center_text("VICTORIAN VILLAGE APARTMENTS", size=14, bold=True)
    center_text("Jim and Jolinda Edwards, d/b/a Victorian Village Apartments", size=10)
    center_text("P.O. Box 471, Nelsonville, Ohio 45764 | 740-707-5851", size=10)
    space(1)

    center_text("NOTICE OF NON-RENEWAL", size=14, bold=True)
    center_text("(Lease Termination)", size=10)
    space(1)

    # Date
    draw_text("Date: _______________________")
    space(0.5)

    # Tenant info
    draw_text("TO:", bold=True)
    space(0.3)
    draw_text("Tenant Name(s): _________________________________________________________________")
    space(0.5)
    draw_text("Unit Address: _____________________________________________, Nelsonville, Ohio 45764")
    space(0.5)
    draw_text("Unit Number: _______________")
    space(1)

    # Notice text
    draw_text("NOTICE:", bold=True)
    space(0.3)
    draw_wrapped("This notice is to inform you that your lease agreement will NOT be renewed upon its expiration.")
    space(0.7)

    draw_text("Current Lease End Date: _______________________")
    space(0.7)

    draw_text("You Must Vacate By: _______________________", bold=True)
    space(1)

    # Move-out requirements
    draw_text("MOVE-OUT REQUIREMENTS:", bold=True)
    space(0.3)
    draw_wrapped("1. Remove all personal belongings from the unit by the vacate date.")
    space(0.3)
    draw_wrapped("2. Clean the unit thoroughly, including appliances, bathroom, and floors.")
    space(0.3)
    draw_wrapped("3. Return all keys to the rental office or rent drop box at 325 S. Harper St.")
    space(0.3)
    draw_wrapped("4. Provide a forwarding address for security deposit return.")
    space(0.3)
    draw_wrapped("5. Schedule a move-out inspection with the landlord.")
    space(1)

    # Deposit info
    draw_text("SECURITY DEPOSIT:", bold=True)
    space(0.3)
    draw_wrapped("Your security deposit will be returned within 30 days of move-out, less any deductions for unpaid rent, damages beyond normal wear and tear, and cleaning costs. An itemized statement will be provided with your deposit return.")
    space(1)

    # Forwarding address
    draw_text("FORWARDING ADDRESS (Required for deposit return):", bold=True)
    space(0.5)
    draw_text("Name: _________________________________________________________________")
    space(0.5)
    draw_text("Address: _________________________________________________________________")
    space(0.5)
    draw_text("City: ____________________________  State: ________  ZIP: _______________")
    space(0.5)
    draw_text("Phone: ____________________________  Email: ______________________________")
    space(1)

    # Signature
    draw_text("_________________________________________          ___________________")
    draw_text("Landlord/Agent Signature                                              Date")
    space(0.5)
    draw_text("Print Name: ___________________________________")
    space(1.5)

    # Tenant acknowledgment
    draw_text("TENANT ACKNOWLEDGMENT:", bold=True)
    space(0.3)
    draw_wrapped("I acknowledge receipt of this Notice of Non-Renewal and understand that I must vacate the premises by the date specified above.")
    space(0.7)

    draw_text("_________________________________________          ___________________")
    draw_text("Tenant Signature                                                          Date")

    c.save()
    print(f"Created: {filename}")
    return filename


def create_deposit_itemization():
    """Generate Security Deposit Itemization Form (ORC § 5321.16)."""
    filename = os.path.join(OUTPUT_DIR, "security-deposit-itemization.pdf")
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    left_margin = 0.75 * inch
    right_margin = width - 0.75 * inch
    top_margin = height - 0.75 * inch
    usable_width = right_margin - left_margin

    y = top_margin
    line_height = 14

    def center_text(text, size=14, bold=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawCentredString(width / 2, y, text)
        y -= size + 6

    def draw_text(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(left_margin + indent, y, text)
        y -= line_height

    def draw_wrapped(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        words = text.split()
        line = ""
        max_width = usable_width - indent

        for word in words:
            test = line + (" " if line else "") + word
            if c.stringWidth(test, font, size) <= max_width:
                line = test
            else:
                c.drawString(left_margin + indent, y, line)
                y -= line_height
                line = word
        if line:
            c.drawString(left_margin + indent, y, line)
            y -= line_height

    def space(lines=0.5):
        nonlocal y
        y -= line_height * lines

    # Header
    center_text("VICTORIAN VILLAGE APARTMENTS", size=14, bold=True)
    center_text("Jim and Jolinda Edwards, d/b/a Victorian Village Apartments", size=10)
    center_text("P.O. Box 471, Nelsonville, Ohio 45764 | 740-707-5851", size=10)
    space(1)

    center_text("SECURITY DEPOSIT ITEMIZATION", size=14, bold=True)
    center_text("(Ohio Revised Code § 5321.16)", size=10)
    space(1)

    # Date
    draw_text("Date: _______________________")
    space(0.5)

    # Tenant info
    draw_text("TO:", bold=True)
    space(0.3)
    draw_text("Former Tenant Name(s): __________________________________________________________")
    space(0.5)
    draw_text("Former Unit Address: _________________________________________, Nelsonville, Ohio 45764")
    space(0.5)
    draw_text("Unit Number: _______________")
    space(0.5)
    draw_text("Move-Out Date: _______________     Move-Out Inspection Date: _______________")
    space(1)

    # Deposit info
    draw_text("SECURITY DEPOSIT ACCOUNTING:", bold=True)
    space(0.5)

    draw_text("Original Security Deposit Paid:                                    $_______________")
    space(0.7)

    draw_text("DEDUCTIONS:", bold=True)
    space(0.5)

    # Deduction items
    draw_text("Unpaid Rent (period: _______________ ):                             $_______________")
    space(0.5)
    draw_text("Unpaid Late Fees:                                                   $_______________")
    space(0.5)
    draw_text("Unpaid Utilities:                                                   $_______________")
    space(0.7)

    draw_text("Damages Beyond Normal Wear and Tear:", bold=True)
    space(0.3)
    draw_text("1. ________________________________________________     $_______________")
    space(0.5)
    draw_text("2. ________________________________________________     $_______________")
    space(0.5)
    draw_text("3. ________________________________________________     $_______________")
    space(0.5)
    draw_text("4. ________________________________________________     $_______________")
    space(0.5)
    draw_text("5. ________________________________________________     $_______________")
    space(0.7)

    draw_text("Cleaning (if not left in clean condition):                          $_______________")
    space(0.7)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_margin, y, "TOTAL DEDUCTIONS:                                                  $_______________")
    y -= line_height * 1.5

    c.setFont("Helvetica-Bold", 11)
    c.drawString(left_margin, y, "AMOUNT REFUNDED TO TENANT:                                         $_______________")
    y -= line_height * 1.5

    space(0.5)

    # Legal notice
    draw_wrapped("Pursuant to Ohio Revised Code § 5321.16, this itemized statement is provided within 30 days of lease termination. Receipts or invoices for deductions are attached where applicable.")
    space(0.5)

    draw_text("Refund Method:   ___  Check enclosed   ___  Direct deposit   ___  Applied to balance owed")
    space(0.5)

    draw_text("Check Number (if applicable): _______________")
    space(1)

    # Balance owed
    draw_text("IF DEDUCTIONS EXCEED DEPOSIT:", bold=True)
    space(0.3)
    draw_text("Amount Owed by Tenant:                                              $_______________")
    space(0.3)
    draw_wrapped("Payment is due within 30 days. Failure to pay may result in collections action and reporting to credit bureaus.")
    space(1)

    # Signature
    draw_text("_________________________________________          ___________________")
    draw_text("Landlord/Agent Signature                                              Date")
    space(0.5)
    draw_text("Print Name: ___________________________________")
    space(1)

    # Attachments
    draw_text("ATTACHMENTS:", bold=True)
    space(0.3)
    draw_text("___  Move-out inspection checklist")
    space(0.3)
    draw_text("___  Photos of damages")
    space(0.3)
    draw_text("___  Repair invoices/receipts")
    space(0.3)
    draw_text("___  Cleaning invoice/receipt")

    c.save()
    print(f"Created: {filename}")
    return filename


def create_extermination_notice():
    """Generate Extermination/Pest Control Notice."""
    filename = os.path.join(OUTPUT_DIR, "extermination-notice.pdf")
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    left_margin = 0.75 * inch
    right_margin = width - 0.75 * inch
    top_margin = height - 0.75 * inch
    usable_width = right_margin - left_margin

    y = top_margin
    line_height = 14

    def center_text(text, size=14, bold=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawCentredString(width / 2, y, text)
        y -= size + 6

    def draw_text(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(left_margin + indent, y, text)
        y -= line_height

    def draw_wrapped(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        words = text.split()
        line = ""
        max_width = usable_width - indent

        for word in words:
            test = line + (" " if line else "") + word
            if c.stringWidth(test, font, size) <= max_width:
                line = test
            else:
                c.drawString(left_margin + indent, y, line)
                y -= line_height
                line = word
        if line:
            c.drawString(left_margin + indent, y, line)
            y -= line_height

    def space(lines=0.5):
        nonlocal y
        y -= line_height * lines

    # Header
    center_text("[Company Name]", size=14, bold=True)
    center_text("[Company Address]", size=10)
    center_text("[Company Phone Number] | [Company Email]", size=10)
    space(1)

    center_text("NOTICE OF EXTERMINATION / PEST CONTROL", size=14, bold=True)
    space(1)

    # Date and recipient
    draw_text("Date: [Current Date]")
    space(0.5)
    draw_text("To: [Recipient First Name] [Recipient Last Name]")
    space(0.3)
    draw_text("Property: [Property Name]")
    space(0.3)
    draw_text("Address: [Property Address]")
    space(1)

    # Notice text
    draw_text("Dear [Recipient First Name] [Recipient Last Name],")
    space(0.5)

    draw_wrapped("This notice is to inform you that extermination/pest control services have been scheduled for your unit. In accordance with your lease agreement, this serves as your 24-hour advance notice of entry.")
    space(0.5)

    draw_text("SCHEDULED SERVICE DATE: _______________________", bold=True)
    space(0.5)
    draw_text("SCHEDULED TIME: _______________________ (approximate)")
    space(0.5)
    draw_text("TYPE OF TREATMENT: _______________________")
    space(1)

    draw_text("PREPARATION REQUIREMENTS:", bold=True)
    space(0.3)
    draw_wrapped("To ensure effective treatment, please complete the following before the scheduled service:")
    space(0.3)
    draw_text("• Remove all items from under sinks and bathroom cabinets", indent=15)
    space(0.3)
    draw_text("• Clear items away from baseboards and walls (12 inches minimum)", indent=15)
    space(0.3)
    draw_text("• Cover or remove pet food and water dishes", indent=15)
    space(0.3)
    draw_text("• Cover fish tanks and turn off air pumps", indent=15)
    space(0.3)
    draw_text("• Remove pets from the unit during treatment", indent=15)
    space(0.3)
    draw_text("• Ensure access to all rooms, closets, and storage areas", indent=15)
    space(1)

    draw_text("AFTER TREATMENT:", bold=True)
    space(0.3)
    draw_wrapped("Do not mop or wash treated areas for at least 14 days to allow treatment to remain effective. Keep children and pets away from treated areas until dry.")
    space(1)

    draw_wrapped("If you have any questions or need to reschedule, please contact us immediately at [Company Phone Number] or [Company Email].")
    space(1)

    draw_text("Sincerely,")
    space(0.5)
    draw_text("[Company Name]")
    space(0.3)
    draw_text("Victorian Village Apartments Management")

    c.save()
    print(f"Created: {filename}")
    return filename


def create_24hour_entry_notice():
    """Generate 24-Hour Notice of Entry."""
    filename = os.path.join(OUTPUT_DIR, "24-hour-entry-notice.pdf")
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    left_margin = 0.75 * inch
    right_margin = width - 0.75 * inch
    top_margin = height - 0.75 * inch
    usable_width = right_margin - left_margin

    y = top_margin
    line_height = 14

    def center_text(text, size=14, bold=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawCentredString(width / 2, y, text)
        y -= size + 6

    def draw_text(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(left_margin + indent, y, text)
        y -= line_height

    def draw_wrapped(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        words = text.split()
        line = ""
        max_width = usable_width - indent

        for word in words:
            test = line + (" " if line else "") + word
            if c.stringWidth(test, font, size) <= max_width:
                line = test
            else:
                c.drawString(left_margin + indent, y, line)
                y -= line_height
                line = word
        if line:
            c.drawString(left_margin + indent, y, line)
            y -= line_height

    def space(lines=0.5):
        nonlocal y
        y -= line_height * lines

    # Header
    center_text("[Company Name]", size=14, bold=True)
    center_text("[Company Address]", size=10)
    center_text("[Company Phone Number] | [Company Email]", size=10)
    space(1)

    center_text("24-HOUR NOTICE OF ENTRY", size=14, bold=True)
    space(1)

    # Date and recipient
    draw_text("Date: [Current Date]")
    space(0.5)
    draw_text("To: [Recipient First Name] [Recipient Last Name]")
    space(0.3)
    draw_text("Property: [Property Name]")
    space(0.3)
    draw_text("Address: [Property Address]")
    space(1)

    # Notice text
    draw_text("Dear [Recipient First Name] [Recipient Last Name],")
    space(0.5)

    draw_wrapped("In accordance with your lease agreement and Ohio law, this notice is to inform you that the landlord or authorized agent will enter your unit for the purpose described below.")
    space(1)

    draw_text("DATE OF ENTRY: _______________________", bold=True)
    space(0.5)
    draw_text("TIME OF ENTRY: _______________________ (approximate)")
    space(1)

    draw_text("PURPOSE OF ENTRY:", bold=True)
    space(0.3)
    draw_text("___  Routine inspection", indent=15)
    space(0.3)
    draw_text("___  Maintenance / Repair: _________________________________________________", indent=15)
    space(0.3)
    draw_text("___  Extermination / Pest control", indent=15)
    space(0.3)
    draw_text("___  Smoke detector / CO detector inspection", indent=15)
    space(0.3)
    draw_text("___  HVAC filter replacement / maintenance", indent=15)
    space(0.3)
    draw_text("___  Showing unit to prospective tenant / buyer", indent=15)
    space(0.3)
    draw_text("___  Other: _________________________________________________", indent=15)
    space(1)

    draw_wrapped("You do not need to be present during this entry. If you have concerns or need to reschedule, please contact us at [Company Phone Number] or [Company Email] as soon as possible.")
    space(1)

    draw_wrapped("Thank you for your cooperation.")
    space(1)

    draw_text("Sincerely,")
    space(0.5)
    draw_text("[Company Name]")
    space(0.3)
    draw_text("Victorian Village Apartments Management")

    c.save()
    print(f"Created: {filename}")
    return filename


def create_general_email_notice():
    """Generate General Email Notice Template."""
    filename = os.path.join(OUTPUT_DIR, "general-email-notice.pdf")
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    left_margin = 0.75 * inch
    right_margin = width - 0.75 * inch
    top_margin = height - 0.75 * inch
    usable_width = right_margin - left_margin

    y = top_margin
    line_height = 14

    def center_text(text, size=14, bold=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawCentredString(width / 2, y, text)
        y -= size + 6

    def draw_text(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(left_margin + indent, y, text)
        y -= line_height

    def draw_wrapped(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        words = text.split()
        line = ""
        max_width = usable_width - indent

        for word in words:
            test = line + (" " if line else "") + word
            if c.stringWidth(test, font, size) <= max_width:
                line = test
            else:
                c.drawString(left_margin + indent, y, line)
                y -= line_height
                line = word
        if line:
            c.drawString(left_margin + indent, y, line)
            y -= line_height

    def space(lines=0.5):
        nonlocal y
        y -= line_height * lines

    # Header
    center_text("[Company Name]", size=14, bold=True)
    center_text("[Company Address]", size=10)
    center_text("[Company Phone Number] | [Company Email]", size=10)
    space(1)

    center_text("TENANT NOTICE", size=14, bold=True)
    space(1)

    # Date and recipient
    draw_text("Date: [Current Date]")
    space(0.5)
    draw_text("To: [Recipient First Name] [Recipient Last Name]")
    space(0.3)
    draw_text("Property: [Property Name]")
    space(0.3)
    draw_text("Address: [Property Address]")
    space(0.3)
    draw_text("Lease Period: [Lease Start Date] to [Lease End Date]")
    space(0.3)
    draw_text("Monthly Rent: [Rental Amount]")
    space(1)

    # Notice text
    draw_text("Dear [Recipient First Name] [Recipient Last Name],")
    space(0.5)

    draw_text("RE: _______________________________________________", bold=True)
    space(1)

    # Message area
    draw_text("MESSAGE:")
    space(0.3)
    c.rect(left_margin, y - 180, usable_width, 185)
    y -= 195
    space(1)

    draw_wrapped("If you have any questions regarding this notice, please contact us at [Company Phone Number] or [Company Email].")
    space(1)

    draw_text("Sincerely,")
    space(0.5)
    draw_text("[Company Name]")
    space(0.3)
    draw_text("Victorian Village Apartments Management")

    c.save()
    print(f"Created: {filename}")
    return filename


def main():
    """Generate all notice documents."""
    print("Generating Ohio-Compliant Notices and Forms...")
    print("=" * 50)

    create_3day_notice()
    create_30day_notice()
    create_nonrenewal_notice()
    create_deposit_itemization()
    create_extermination_notice()
    create_24hour_entry_notice()
    create_general_email_notice()

    print("=" * 50)
    print("Done!")


if __name__ == "__main__":
    main()
