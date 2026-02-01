#!/usr/bin/env python3
"""
Generate Victorian Village Lease PDFs for Innago.
Creates 4 versions: 1-person, 2-person, 3-person, 4-person leases.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def create_lease_pdf(num_tenants: int):
    """Generate a lease PDF for the specified number of tenants."""
    filename = os.path.join(OUTPUT_DIR, f"victorian-village-lease-{num_tenants}-person.pdf")
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # Margins
    left_margin = 0.75 * inch
    right_margin = width - 0.75 * inch
    top_margin = height - 0.75 * inch
    usable_width = right_margin - left_margin

    y = top_margin
    line_height = 14  # Increased for more spacing
    para_spacing = 6

    def new_page():
        nonlocal y
        c.showPage()
        y = top_margin

    def check_page(needed=1.5):
        if y < needed * inch:
            new_page()

    def center_text(text, size=14, bold=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawCentredString(width / 2, y, text)
        y -= size + 4

    def draw_text(text, size=10, bold=False, indent=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(left_margin + indent, y, text)
        y -= line_height

    def draw_wrapped(text, size=10, bold=False, indent=0, hanging=0):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        words = text.split()
        line = ""
        first_line = True
        max_width = usable_width - indent - hanging

        for word in words:
            test = line + (" " if line else "") + word
            if c.stringWidth(test, font, size) <= max_width:
                line = test
            else:
                x = left_margin + indent + (0 if first_line else hanging)
                c.drawString(x, y, line)
                y -= line_height
                check_page()
                c.setFont(font, size)  # Reset font after page break
                line = word
                first_line = False
        if line:
            x = left_margin + indent + (0 if first_line else hanging)
            c.drawString(x, y, line)
            y -= line_height

    def space(lines=0.5):
        nonlocal y
        y -= line_height * lines

    # ==================== HEADER ====================
    center_text("VICTORIAN VILLAGE APARTMENTS", size=14, bold=True)
    center_text("P.O. Box 471, Nelsonville, Ohio 45764", size=10)
    center_text("740-707-5851", size=10)
    space(0.5)
    center_text("RESIDENTIAL LEASE AGREEMENT", size=12, bold=True)
    space(1)

    # Lessor info
    draw_text("LESSOR INFORMATION", bold=True)
    space(0.5)
    draw_text("Property Owner(s): Jim and Jolinda Edwards")
    space(0.3)
    draw_text("d/b/a Victorian Village Apartments")
    space(0.3)
    draw_text("P.O. Box 471, Nelsonville, Ohio 45764")
    space(0.7)

    # Date line
    draw_text("THIS LEASE AGREEMENT is made this _____ day of _____________, 20___, by and between")
    draw_text("Jim and Jolinda Edwards, d/b/a Victorian Village Apartments, hereinafter designated as")
    draw_text("\"Lessor,\" and the following individual(s), hereinafter designated as \"Lessee(s)\":")
    space(1)

    # ==================== TENANT INFORMATION ====================
    draw_text("TENANT INFORMATION", bold=True)
    space(0.5)

    for i in range(1, num_tenants + 1):
        draw_text(f"Tenant {i}: _________________________________ DOB: ____________")
        space(0.4)
        draw_text("Phone: _________________________ Email: _________________________________")
        space(0.4)
        draw_text("SS#: ___________________________")
        space(0.4)
        draw_text("Emergency Contact: _________________________ Phone: _______________________")
        space(0.4)
        if num_tenants == 1:
            draw_text("Responsibility: 100% (Whole)")
        elif num_tenants == 2:
            draw_text("Responsibility:   100% (Whole) ___   50% (Half) ___")
        elif num_tenants == 3:
            draw_text("Responsibility:   100% (Whole) ___   50% (Half) ___   33.3% (Third) ___")
        elif num_tenants == 4:
            draw_text("Responsibility:   100% ___   50% ___   33.3% ___   25% ___")
        space(0.6)

    space(0.5)

    # ==================== PROPERTY INFORMATION ====================
    draw_text("PROPERTY INFORMATION", bold=True)
    space(0.5)
    draw_text("Unit Address: _______________________________________, Nelsonville, Ohio 45764")
    space(0.4)
    draw_text("Unit Number: _______________")
    space(0.5)
    draw_text("Unit Type:   Single ___   Double ___   2 Bed Townhouse ___   3 Bed Townhouse ___")
    space(0.3)
    draw_text("             2 Bed / 2 Bath Studio ___")
    space(1)

    # ==================== LEASE TERMS ====================
    draw_text("LEASE TERMS", bold=True)
    space(0.5)
    draw_text("Lease Term:   9 Months ___   12 Months ___")
    space(0.5)
    draw_text("Lease Start Date: _____________________     Lease End Date: _____________________")
    space(0.5)
    draw_text("Monthly Rent: $_____________     Security Deposit: $_____________")
    space(1)

    # ==================== WITNESSETH ====================
    draw_text("WITNESSETH:", bold=True)
    space(0.3)
    draw_wrapped("The Lessor, in consideration of the rent reserved herein to be paid by said Lessee(s) and of the other covenants, rules, agreements, and conditions hereinafter contained to be kept, performed, and observed by said Lessee(s), does hereby let and lease unto said Lessee(s) the above-described premises in the Victorian Village Apartments located in the City of Nelsonville, County of Athens, and State of Ohio, to be used and occupied by the Lessee(s) as a private residence, and for no other purpose, for the term specified above.")
    space(1)

    check_page(2)

    # ==================== SECTION 1: RENT ====================
    draw_text("1. RENT PAYMENT.", bold=True)
    draw_wrapped("Lessee(s) shall pay each month during the term the sum specified above as basic rent. Rent is due on the FIRST (1st) day of each month. Accepted payment methods: (1) Innago online portal, (2) check mailed to P.O. Box 471, Nelsonville, Ohio 45764, or (3) cash or check in rent drop box at 325 S. Harper St. No post-dated or third-party checks accepted.", indent=0)
    space(0.5)

    # ==================== SECTION 2: LATE FEES ====================
    draw_text("2. LATE FEES.", bold=True)
    draw_wrapped("If rent is not received by the FIFTH (5th) day of the month, a late fee of TWENTY-FIVE DOLLARS ($25.00) will be assessed.", indent=0)
    space(0.5)

    # ==================== SECTION 3: JOINT LIABILITY AND RESPONSIBILITY ====================
    draw_text("3. JOINT LIABILITY AND RESPONSIBILITY.", bold=True)
    draw_wrapped("All Lessee(s) executing this Lease are jointly and severally liable for 100% of all rent, fees, deposits, damages, internet charges, and expenses charged to the account. The responsibility percentage listed above is for internal billing and payment arrangement purposes only and does not limit any Lessee's legal liability for the full amount due. Lessor may pursue any one or all Lessees for the entire balance owed.", indent=0)
    space(0.5)

    check_page(2)

    # ==================== SECTION 4: CONDITION ====================
    draw_text("4. CONDITION OF PREMISES.", bold=True)
    draw_wrapped("The Lessee(s) accepts said premises in their present condition, and agrees to keep said premises in a good and clean condition; to make no alterations, including partitions, to the same; to commit no waste thereon; to obey all laws and ordinances affecting said premises; to repay the Lessor the cost of all repairs made necessary by the negligent or careless use of said premises; to obey and abide by the rules and fees specifically itemized in this lease; and to surrender the premises at the termination hereof in like condition as when taken.", indent=0)
    space(0.5)

    # ==================== SECTION 5: POSSESSION ====================
    draw_text("5. INABILITY TO DELIVER POSSESSION.", bold=True)
    draw_wrapped("It is understood that if the Lessee(s) shall be unable to enter and occupy the premises at the time above provided by reason of said premises not being ready for occupancy, or by reason of the holding over of any previous occupant of said premises, or as a result to any cause or reason beyond the control of the Lessor, the Lessor shall not be liable in damages to the Lessee(s). If said Lessor is not able to deliver possession to said Lessee(s) within five days of the date named for the commencement of said term, the Lessee(s) may cancel and terminate the Lease.", indent=0)
    space(0.5)

    check_page(2)

    # ==================== SECTION 6: DAMAGE ====================
    draw_text("6. DAMAGE OR DESTRUCTION.", bold=True)
    draw_wrapped("In case of partial destruction or injury to said premises by fire, the elements, or other casualties, the Lessor shall repair the same with reasonable dispatch after notice to him in writing of such destruction or injury. The Lessee(s) shall be liable for all such destruction or injury to the premises caused by Lessee's negligence or violation of any covenant, rule, or regulation within this Lease. In the event the premises are rendered totally untenantable by fire, the elements, or other casualty, or in the event the building of which the demised premises are a part, though the demised premises may not be affected, is so injured or destroyed that the Lessor shall decide within a reasonable time not to rebuild, the term hereby granted shall cease and the rent shall be paid up to the date of such injury or damage.", indent=0)
    space(0.5)

    check_page(2)

    # ==================== SECTION 7: UTILITIES (UPDATED) ====================
    draw_text("7. UTILITIES.", bold=True)
    draw_wrapped("Lessor shall furnish water, sewer, and refuse removal for ordinary domestic use. Lessee(s) shall pay for all other utility services, including but not limited to electric service. Internet service is billed separately as described in Section 8.", indent=0)
    space(0.5)

    check_page(3)

    # ==================== SECTION 8: INTERNET SERVICE (UPDATED) ====================
    draw_text("8. INTERNET SERVICE.", bold=True)
    draw_wrapped("Internet service is provided to the premises by ERE Fiber LLC (\"ERE Fiber\"). Internet service is REQUIRED for all units and cannot be opted out of. By occupying the premises, Lessee(s) agrees to the following terms:", indent=0)
    space(0.3)

    draw_wrapped("a. REQUIRED SERVICE AND BILLING: High-speed fiber internet service (500 Mbps) is REQUIRED for all units at $45.00 per month. Internet service is billed as a separate line item on the monthly invoice in addition to the base rent amount. This is a mandatory utility charge that applies to all units.", indent=15, hanging=15)
    space(0.3)

    draw_wrapped("b. EQUIPMENT: (i) ERE Fiber provides and owns the Optical Network Terminal (ONT), which is the fiber connection device installed at the premises. The ONT remains the property of ERE Fiber and must not be tampered with, moved, or removed. (ii) LESSEE IS RESPONSIBLE FOR PROVIDING THEIR OWN WIRELESS ROUTER. The ONT provides a wired ethernet connection only. To use WiFi, Lessee(s) must purchase and configure their own wireless router. (iii) ERE Fiber is not responsible for Lessee's router, WiFi coverage, or connectivity issues caused by Lessee's equipment.", indent=15, hanging=15)
    space(0.3)

    check_page(2)

    draw_wrapped("c. SERVICE TERMS: Internet service is subject to ERE Fiber's Terms of Service and Acceptable Use Policy, available at erefiber.com. Lessee(s) agrees to comply with all terms and policies.", indent=15, hanging=15)
    space(0.3)

    draw_wrapped("d. INTERNET SUSPENSION FOR NON-PAYMENT: If rent and/or internet charges remain unpaid after the FIFTH (5th) day of the month, Lessor may authorize ERE Fiber to suspend internet service. Lessee(s) will receive 72 hours advance written notice before any suspension. Service will be restored within 24 hours of payment. Suspension does not waive Lessee's obligation to pay for internet service during suspension.", indent=15, hanging=15)
    space(0.3)

    draw_wrapped("e. RESIDENTIAL USE ONLY: Internet service is for personal, residential use only. The following activities are strictly prohibited: (i) Operating public-facing servers (web, email, game, FTP, or media servers); (ii) Running commercial online services or applications; (iii) Reselling internet access to third parties; (iv) Operating large-scale file sharing or streaming services; (v) Running cryptocurrency mining operations.", indent=15, hanging=15)
    space(0.3)

    check_page(2)

    draw_wrapped("f. ILLEGAL ACTIVITIES PROHIBITED: Lessee(s) shall not use internet service for any illegal purpose, including but not limited to: (i) Copyright infringement, including unauthorized downloading or distribution of copyrighted materials; (ii) Unauthorized access to computers, networks, or accounts; (iii) Distribution of malware, viruses, or malicious software; (iv) Sending spam or phishing emails; (v) Any activity that violates federal, state, or local law.", indent=15, hanging=15)
    space(0.3)

    draw_wrapped("g. SPEED UPGRADES: Lessee(s) may request speed upgrades (1 Gbps or 2 Gbps) by submitting a maintenance request. Upgrades are subject to availability and additional monthly charges will be added to the invoice.", indent=15, hanging=15)
    space(0.3)

    draw_wrapped("h. CONSEQUENCES OF VIOLATIONS: Violations of internet service terms may result in: (i) Warning requiring immediate corrective action; (ii) Suspension or termination of internet service; (iii) Lessee(s) being held financially responsible for investigation costs, damages, and legal fees; (iv) Referral to law enforcement for illegal activities; (v) Termination of this Lease at Lessor's discretion.", indent=15, hanging=15)
    space(0.3)

    draw_wrapped("i. SUPPORT: For internet service issues, Lessee(s) should submit a maintenance request through the tenant portal. Issues will be forwarded to ERE Fiber for resolution.", indent=15, hanging=15)
    space(0.5)

    check_page(2)

    # ==================== SECTION 9: RIGHT OF ENTRY ====================
    draw_text("9. RIGHT OF ENTRY.", bold=True)
    draw_wrapped("The Lessor, his agents and employees may enter said premises at any time with a key or otherwise to examine same or to make needed repairs to said premises upon 24 hours notice to the Lessee(s), or in lieu of 24 hours notice at the request of any said lessee of the applicable apartment. Said 24-hour notice shall not be necessary where it is impracticable to give the same or if there is an emergency situation. It is agreed by all parties to this lease that a pest control service schedule given to each lessee at the beginning of said lease giving notice of a monthly pest control treatment shall meet the statutory 24-hour notice requirement. Similarly, Lessor, its agents and employees may enter the premises at reasonable times to install or repair pipes, wires, and other appliances deemed by the Lessor essential to the use and occupation of other parts of the building, and to perform extraordinary pest control services with 24 hours notice, except in the case of impracticable or emergency situations. Inside chain or security locks are prohibited.", indent=0)
    space(0.5)

    # ==================== SECTION 10: SUBLETTING AND ROOMMATE REPLACEMENT ====================
    draw_text("10. SUBLETTING AND ROOMMATE REPLACEMENT.", bold=True)
    draw_wrapped("Lessee(s) shall not sublet the premises, or any part thereof, or assign this Lease, without the prior written consent of the Lessor. If one tenant in a multi-tenant lease wishes to vacate before the lease term ends, that tenant must provide 30 days written notice and may propose a qualified replacement. Replacement tenants must meet Lessor's standard screening criteria (credit, income, rental history). Lessor will not unreasonably withhold approval and will respond within 14 days of receiving a completed application. Departing tenant remains liable for their share until replacement signs a lease addendum and takes possession. If no qualified replacement is approved within 30 days of notice, departing tenant remains liable for their share through lease end.", indent=0)
    space(0.5)

    check_page(2)

    # ==================== SECTION 11: PETS ====================
    draw_text("11. PETS.", bold=True)
    draw_wrapped("No pets of any kind are permitted on the premises.", indent=0)
    space(0.5)

    # ==================== SECTION 12: QUIET ENJOYMENT AND GUESTS ====================
    draw_text("12. QUIET ENJOYMENT AND GUESTS.", bold=True)
    draw_wrapped("Lessee(s) shall not disturb, annoy, endanger, or interfere with other tenants of the building or neighbors. Quiet hours are from 10:00 PM to 8:00 AM. Guests are welcome but may not stay more than forty-eight (48) hours in any seven (7) day period without prior written consent from Lessor. Any person staying beyond this limit will be considered an unauthorized occupant, which is a material violation of this lease. Lessee(s) is responsible for the conduct of all guests.", indent=0)
    space(0.5)

    # ==================== SECTION 13: PARKING ====================
    draw_text("13. PARKING.", bold=True)
    draw_wrapped("ONE parking pass will be issued to each tenant IF a vehicle is listed on the front of this lease. This permit is to be posted in the front windshield clearly. In the event you change your vehicle for any reason, you need to exchange the parking pass. ALL vehicles parked outside of visitors parking without a valid pass will be towed at owner's expense. It will be tenant's responsibility to change the vehicle type on front of lease, if applicable. $10.00 fee for replacement of pass. No trailers, motor homes, or boats will be allowed to park on the premises, save with the written consent of the Lessor. No vehicles are permitted on property with flat tires or inoperable. They are subject to being towed.", indent=0)
    space(0.5)

    check_page(2)

    # ==================== SECTION 14: SMOKE-FREE ====================
    draw_text("14. SMOKE-FREE PREMISES.", bold=True)
    draw_wrapped("Smoking is prohibited inside all units and within 25 feet of any building. This includes cigarettes, cigars, pipes, e-cigarettes, and vaping devices. Violations of this policy will result in a $50 fine per incident and may constitute grounds for lease termination under Section 15 (Default).", indent=0)
    space(0.5)

    # ==================== SECTION 15: DEFAULT ====================
    draw_text("15. DEFAULT.", bold=True)
    draw_wrapped("If Lessee(s) fails to pay rent when due, violates any provision of this Lease, or abandons the premises, Lessor may terminate this Lease and pursue all remedies available under Ohio law, including eviction proceedings.", indent=0)
    space(0.5)

    # ==================== SECTION 16: SECURITY DEPOSIT ====================
    draw_text("16. SECURITY DEPOSIT.", bold=True)
    draw_wrapped(f"Lessee(s) has deposited with Lessor the amount specified above as security for the full and complete performance of the duties and obligations imposed upon the Lessee(s) by the terms and provisions of the lease. In the event of a default by the Lessee(s) in such performance, Lessor may apply such portions of such deposit as necessary in order to compensate Lessor for any damages sustained by Lessor by reason of such default. All portions of such deposit which are not so applied shall be returned to Lessee(s) within 30 days of the expiration of this lease and delivery of possession, provided that Lessee(s) has occupied the premises or paid rent for same for full term of this lease. In the event that the Lessee(s) vacates the premises prior to the expiration of the lease term, in addition to other remedies due Lessor, the entire Security Deposit will be retained by the Lessor to cover its costs in obtaining another occupant for the premises vacated. IN NO CASE CAN THE LESSEE(S) USE THE SECURITY DEPOSIT AS THE LAST MONTH'S RENT! Lessee(s) further covenants and agrees that upon the expiration of said term or upon the termination of the Lease for any cause, he/she will yield immediate possession to Lessor and return the keys for said premises to Lessor. Lessee(s) agrees to vacate premises in clean condition and notify in writing to Lessor 30 days in advance of his/her intention to vacate. Security Deposits will be returned only if proper notice is given as required by the landlord and the law of the State of Ohio. Furthermore, all other requirements of the law as to the return of security deposits must be strictly complied with. Lessee will be responsible for removal of smoke odor if applicable.", indent=0)
    space(0.5)

    check_page(2)

    # ==================== SECTION 17: NOTICES ====================
    draw_text("17. NOTICES.", bold=True)
    draw_wrapped("All notices required or permitted under this Lease shall be in writing and shall be delivered personally, sent by certified mail, or sent via email to the addresses provided above.", indent=0)
    space(0.5)

    # ==================== SECTION 18: ENTIRE AGREEMENT ====================
    draw_text("18. ENTIRE AGREEMENT.", bold=True)
    draw_wrapped("This Lease constitutes the entire agreement between the parties. No oral agreements or representations shall be binding. Any modifications must be in writing and signed by both parties.", indent=0)
    space(0.5)

    # ==================== SECTION 19: GOVERNING LAW AND FAIR HOUSING ====================
    draw_text("19. GOVERNING LAW AND FAIR HOUSING.", bold=True)
    draw_wrapped("This Lease shall be governed by the laws of the State of Ohio. Venue for any legal action shall be in Athens County, Ohio. Lessor complies with the Fair Housing Act (42 U.S.C. § 3601 et seq.) and does not discriminate based on race, color, religion, sex, national origin, familial status, or disability.", indent=0)
    space(0.5)

    # ==================== SECTION 20: BEDBUG DISCLOSURE ====================
    draw_text("20. BEDBUG DISCLOSURE.", bold=True)
    draw_wrapped("Lessor has no knowledge of bedbug infestation in the unit as of the lease start date. Lessee(s) shall immediately notify Lessor in writing of any suspected infestation. Lessee(s) is responsible for treatment costs if infestation is caused by Lessee's actions or belongings.", indent=0)
    space(0.5)

    # ==================== SECTION 21: SMOKE AND CO DETECTORS ====================
    draw_text("21. SMOKE AND CARBON MONOXIDE DETECTORS.", bold=True)
    draw_wrapped("Lessor certifies that working smoke detectors and carbon monoxide detectors are installed in the unit as required by Ohio Revised Code §§ 3781.111 and 3781.105. Lessee(s) agrees to: (1) test detectors monthly; (2) notify Lessor immediately if any detector malfunctions or needs battery replacement; (3) NOT disable, remove, or tamper with any detector. Disabling smoke or CO detectors is a material violation of this lease and may result in termination. Lessee(s) may be held liable for injuries or damages resulting from disabled detectors.", indent=0)
    space(0.5)

    check_page(2)

    # ==================== SECTION 22: KEYS ====================
    draw_text("22. KEYS.", bold=True)
    draw_wrapped(f"Lessee(s) will receive unit keys on the lease start date. Each tenant receives one (1) door key and one (1) mailbox key ({num_tenants} door key(s) and {num_tenants} mailbox key(s) total for this lease). Lessee(s) shall not make copies of keys or change locks without written consent from Lessor. Upon move-out, all keys must be returned. Lost key replacement fee: $25.00. Lock change fee (if keys not returned): $75.00.", indent=0)
    space(0.5)

    check_page(2)

    # ==================== SECTION 23: PARTIAL EVICTION ====================
    draw_text("23. PARTIAL EVICTION.", bold=True)
    draw_wrapped("The Lessee(s) covenants that in the event of a partial eviction occasioned by any act or neglect of the Lessor that does not materially affect the beneficial use by the Lessee, the obligation to pay rent shall not abate but possession shall be restored or the rent shall be reduced proportionately at the option of the Lessor.", indent=0)
    space(0.5)

    # ==================== SECTION 24: LESSEE COVENANTS ====================
    draw_text("24. LESSEE COVENANTS.", bold=True)
    draw_wrapped("The Lessee(s) covenants and agrees that he/she (a) will keep the part of the premises he uses and occupies safe and sanitary; (b) will dispose of all rubbish, garbage and other wastes in a clean, safe and sanitary manner in the large outside steel dumpsters only; (c) will keep all plumbing fixtures in the dwelling unit or used by him clean; (d) will use and operate all electrical and plumbing fixtures functioning properly and comply with the requirements imposed by all applicable State and local housing, health and safety codes; (e) will refrain and forbid any other person who is on his premises with his permission from intentionally or negligently destroying, defacing, damaging or removing any fixture, appliance or other parts of the premises; (f) will keep in good working order and condition and keep clean any range, refrigerator, furnace filter, smoke alarms, or other appliance supplied by the Lessor; and (g) will conduct himself and require others on the premises with his consent to conduct themselves in a manner which will not disturb his neighbors' peaceful enjoyment. Lessee(s) further covenants that he will be liable for all fees itemized in this lease, and that he will be responsible for all applicable fees incurred by acts and omissions of his family and guests.", indent=0)
    space(0.5)

    check_page(2)

    # ==================== SECTION 25: LIMITATION OF LIABILITY ====================
    draw_text("25. LIMITATION OF LIABILITY.", bold=True)
    draw_wrapped("The Lessee(s) covenants that the Lessor shall not be liable for any damage or injury of the Lessee(s), the Lessee's agents or the Lessee's children or to any person entering the premises or the building of which the demised premises are a part or to goods or machinery or other chattels therein resulting from any defect in the structure or its equipment, or in the structure or equipment of the structure of which the demised premises are a part and further to indemnify and save the Lessor harmless from all claims of every kind and nature. Victorian Village Apartments advises all tenants to obtain their own \"Apartment Dwellers Insurance\" as the Lessor's insurance policy does not cover tenant belongings.", indent=0)
    space(0.5)

    check_page(2)

    # ==================== SECTION 26: HOLDOVER TENANCY ====================
    draw_text("26. HOLDOVER TENANCY.", bold=True)
    draw_wrapped("The Lessee(s) covenants that his/her occupancy of the said premises beyond the term of this lease shall not be deemed as a renewal of this lease for the whole term or any part thereof, but that the acceptance by the Lessor of rent accruing after the expiration of this lease shall be considered as a lease for one month only and for successive periods of one month only. This only occurs with permission from the Lessor.", indent=0)
    space(0.5)

    # ==================== SECTION 27: NO AUTOMATIC RENEWAL ====================
    draw_text("27. NO AUTOMATIC RENEWAL.", bold=True)
    draw_wrapped("Absolutely no option to renew lease. There shall be no option of the lessee(s) to renew this lease. Lessee(s) may apply for a new lease on the premises without having to pay an application fee. Lessee(s) must notify Lessor in writing sixty (60) days in advance of the termination date of the Lease of their wish to apply for this apartment. Failure to provide such notification will be considered by the Lessor as Lessee's intent that Lessee(s) does not wish to lease the apartment.", indent=0)
    space(0.5)

    # ==================== SECTION 28: LEASE VIOLATIONS ====================
    draw_text("28. LEASE VIOLATIONS.", bold=True)
    draw_wrapped("Lessee(s) on this lease in violation of any rule, regulation, or covenant of this lease or their current lease prior to the beginning of this lease shall be subject to the immediate cancellation of this lease at the discretion of Lessor.", indent=0)
    space(0.5)

    check_page(2)

    # ==================== SECTION 29: LEGAL PROCEEDINGS ====================
    draw_text("29. LEGAL PROCEEDINGS.", bold=True)
    draw_wrapped("In the event of legal proceedings being instituted to collect for past due rent, damages, unpaid bills, or evict Lessee(s), said Lessee(s) shall be liable to the Lessor for all court costs.", indent=0)
    space(0.5)

    # ==================== SECTION 30: ABANDONMENT ====================
    draw_text("30. ABANDONMENT.", bold=True)
    draw_wrapped("If said premises shall be abandoned, deserted or vacated, then it shall be lawful for said Lessor, his agents, attorney, successors or assigns to reenter, repossess said premises and upon reentry as aforesaid this Lease shall terminate. However, Lessee(s) shall remain liable for all covenants of this lease breached and for all future rents under the terms of this lease until the apartment is re-rented along with the applicable administrative and advertising costs of re-renting the apartment. An apartment shall be considered abandoned if the monthly rent is past due for 30+ days, utilities are disconnected at tenant's request, and the tenant does not respond to written notice at premises and emergency contact addresses within 7 days.", indent=0)
    space(0.5)

    check_page(2)

    # ==================== SECTION 31: BINDING EFFECT ====================
    draw_text("31. BINDING EFFECT.", bold=True)
    draw_wrapped("It is understood and agreed that the terms Lessor and Lessee(s) shall include the executors, administrators, successors, heirs and assigns of the parties hereto.", indent=0)
    space(0.5)

    # ==================== SECTION 32: RETURNED CHECKS ====================
    draw_text("32. RETURNED CHECKS.", bold=True)
    draw_wrapped("In the event Lessor or its agent is required to process a check of the Lessee(s) which has been returned by the bank for any reason, the Lessor or its agent will notify said Lessee(s) and thereupon the amount of that check plus a handling charge of $25.00 shall become due and payable within 24 hours of said notification. Lessee(s) rent shall be considered unpaid until paid by money order or certified check. All subsequent rents, fees, etc. due Lessor shall be paid by money order or certified check by Lessee(s) who have given a check returned by their bank for any reason.", indent=0)
    space(0.5)

    # ==================== SECTION 33: LESSOR'S RIGHTS ====================
    draw_text("33. LESSOR'S RIGHTS.", bold=True)
    draw_wrapped("Lessor shall have the right at all times to require strict compliance with all covenants and provisions of this lease, notwithstanding any conduct or custom on the part of the Lessor in refraining from so doing at any time or times, and the waiver by Lessor at any time of any breach or condition of this lease by the Lessee shall not be or affect any change in the terms hereof or constitute or become a waiver of a subsequent breach, and Lessor may discontinue any facilities furnished and services rendered by the Lessor, not expressly covenanted for herein, it being expressly understood that they constitute no part of the consideration for this lease. Furthermore, Lessor may initiate eviction procedures against any Lessee(s) upon the statutorily required notice for any breach of any covenant, rule, or regulation of this lease, and Lessee shall remain liable for any unpaid rents, fees, and waste committed upon the premises. In addition, if Lessee(s) is evicted he shall remain liable for the balance of all future rents and the expenses of re-renting the apartment due under the terms of this lease until the apartment is re-rented.", indent=0)
    space(0.5)

    check_page(2)

    # ==================== SECTION 34: ELECTRIC SERVICE ====================
    draw_text("34. ELECTRIC SERVICE.", bold=True)
    draw_wrapped("Tenant(s) must have the electric service provided by AEP for the applicable apartment put in their name(s) no later than the beginning date of this lease, and leave said electric service in the tenant(s) name(s) until the ending date of this lease. Failure to comply will result in the tenant(s) being charged a $50.00 bookkeeping fee and being billed for the applicable electric charges.", indent=0)
    space(0.5)

    check_page(3)

    # ==================== SECTION 35: RULES AND REGULATIONS ====================
    draw_text("35. RULES AND REGULATIONS.", bold=True)
    draw_wrapped("Lessee(s) agrees and covenants that he will abide by the covenants contained herein and the rules and regulations listed below and that failure to abide by any one of such covenants, rules, and regulations shall constitute a breach of this lease allowing Lessor to evict Lessee(s) and hold Lessee(s) liable for all rents due, past, present, and future, and any other applicable damages incurred by Lessor:", indent=0)
    space(0.3)

    draw_wrapped("a. The yards, sidewalks, halls, passages, and stairways shall not be obstructed by any of the tenants, or used by them for any other purpose than those of ingress and egress to and from their respective apartments; nor shall any tenant, tenant's guest, or employee of any tenant go upon the roof under any conditions.", indent=15, hanging=15)
    space(0.2)

    draw_wrapped("b. Floors, doors and windows reflecting or admitting light into passageways or elsewhere in the building shall not be covered or obstructed by Lessee(s) and nothing shall be thrown by Lessee(s) out of the windows or doors or down the passages, halls, or elevators of the buildings.", indent=15, hanging=15)
    space(0.2)

    draw_wrapped("c. The Lessor shall in all cases retain the right to control and prevent access to the building or any part thereof, of all persons whose presence, in the judgment of the Lessor, or its employees, shall be prejudicial to the safety, character, reputation or interests of the building or its occupants.", indent=15, hanging=15)
    space(0.2)

    check_page(2)

    draw_wrapped("d. The toilets and water apparatus shall not be used for any purpose other than that for which they are constructed, and no sweepings, rubbish, rags, ashes, medicines, chemicals, sanitary napkins, or other improper articles shall be thrown therein. Any damage resulting by such misuse shall be borne by the Lessee(s).", indent=15, hanging=15)
    space(0.2)

    draw_wrapped("e. No signs, awnings, screens, paper, advertisements or notices shall be placed or fixed upon any part of the premises, outside or inside, nor shall any articles be suspended outside the building or placed on the windows or window sills thereof, save with the consent, in writing, of the Lessor.", indent=15, hanging=15)
    space(0.2)

    draw_wrapped("f. No tenant shall do or suffer or permit anything to be done in said premises, or bring or keep anything therein which will in any manner be construed to be a fire hazard or increase the rate of fire insurance on said building. No extension cords shall be permitted, except power strips and heavy duty extension cords as approved by the City of Nelsonville Fire Department and Office of Code Enforcement.", indent=15, hanging=15)
    space(0.2)

    check_page(2)

    draw_wrapped("g. No noisy or disorderly conduct or conduct annoying or disturbing to other occupants of the building shall be permitted. Underage alcohol consumption or illegal drugs of any kind is not allowed on the premises, and its discovery will result in immediate eviction of the culpable party and/or lessee(s) of the applicable apartment.", indent=15, hanging=15)
    space(0.2)

    draw_wrapped("h. No pets of any kind, including but not limited to domestic or wild animals and birds, shall be maintained in or about the building; not even to visit, and the Lessee(s) authorize Lessor to remove any such pet found in the apartment or on the apartment building premises to the local animal shelter, and to charge Lessee(s) the cost of removing and transporting said pet, such charge to be a minimum of $50.00.", indent=15, hanging=15)
    space(0.2)

    draw_wrapped("i. No picture hooks, nails or other devices for suspending pictures, mirrors, etc. shall be driven in any part of the building, nor shall any portion of the same be marked, defaced, or otherwise altered, save with the written consent of the Lessor.", indent=15, hanging=15)
    space(0.2)

    check_page(2)

    draw_wrapped("j. Any fixtures or chattels left in the premises upon the termination of this lease shall be declared abandoned and will become the property of the Lessor.", indent=15, hanging=15)
    space(0.2)

    draw_wrapped("k. No additional electric pipes or wires or radiators or fixtures of any kind shall be put in or changed or in any way altered, save with the written consent of the Lessor.", indent=15, hanging=15)
    space(0.2)

    draw_wrapped("l. The Lessor reserves the right to prescribe the weight and proper position of heavy articles, and the manner of placing them in position. Beer kegs are absolutely prohibited from the premises.", indent=15, hanging=15)
    space(0.2)

    draw_wrapped("m. Property left by or for tenants with employees of the Lessor will be received by such person as agents of the Lessee(s) and Lessor will not be responsible for its loss or damage.", indent=15, hanging=15)
    space(0.2)

    check_page(2)

    draw_wrapped("n. Lessee(s) shall not use any electrical appliance that will interfere in any way with the radio or television reception of other tenants, nor in any event build or use any outside aerials for any purpose.", indent=15, hanging=15)
    space(0.2)

    draw_wrapped("o. Lessee(s) shall install only draperies on any exterior window or door and all draperies must be white or lined with white fabric and must cover the entire glass area in the window or door. In the event of failure to comply with this rule after one warning notice, lessee(s) authorize Lessor to enter Lessee(s) apartment, remove the existing draperies, replace them with draperies that comply with this rule, and charge the Lessee(s) for the new draperies and an installation charge of $50.00.", indent=15, hanging=15)
    space(0.2)

    draw_wrapped("p. No waterbeds are permitted on the premises, save with the written permission of the Lessor and compliance with certain insurance requirements.", indent=15, hanging=15)
    space(0.2)

    check_page(2)

    draw_wrapped("q. No trailers, motor homes, or boats will be allowed to park on the premises, save with the written consent of the Lessor. No vehicles are permitted on property with flat tires or inoperable. They are subject to being towed.", indent=15, hanging=15)
    space(0.2)

    draw_wrapped("r. No assemblies of any nature shall be held in any apartment that exceed eight (8) persons or four (4) times the number of tenants occupying said apartment including the tenants occupying the apartment, whichever number is greater.", indent=15, hanging=15)
    space(0.2)

    draw_wrapped("s. Any tenant found vandalizing or attempting to circumvent the security door system will be immediately prosecuted and evicted.", indent=15, hanging=15)
    space(0.2)

    draw_wrapped("t. Absolutely no Hookah pipes used in apartments.", indent=15, hanging=15)
    space(0.5)

    check_page(3)

    # ==================== SECTION 36: FEES ====================
    draw_text("36. FEES.", bold=True)
    draw_wrapped("Lessee(s) agrees to pay the following fees when applicable:", indent=0)
    space(0.3)

    draw_text("a. Lease Change ................................. $30.00", indent=15)
    draw_text("b. Lock Out (to 11 P.M.) ....................... $10.00; After 11 P.M. - $25.00", indent=15)
    draw_text("c. Keys Made ................................... $5.00 per key", indent=15)
    draw_text("d. Check Returned by Bank ...................... $25.00", indent=15)
    draw_text("e. Lock Change ................................. $35.00", indent=15)
    draw_text("f. Removal of Trash Per Bag .................... $20.00", indent=15)
    draw_text("g. Cleaning Refrigerator ....................... $40.00", indent=15)
    draw_text("h. Cleaning of Apartment (extensive) ........... $10.00 per hour per person", indent=15)
    draw_text("i. Non-Return of Key ........................... $25.00", indent=15)
    draw_text("j. Painting and patching ....................... $12.00/hr/person + materials", indent=15)
    draw_text("k. Structural Damage ........................... $15.00/hr/person + materials", indent=15)
    draw_text("l. Light fixtures, Traverse rods, etc. ........ $12.00/hr/person + materials", indent=15)
    draw_text("m. Plumbing/electrical repair (tenant fault) ... $12.00/hr/person + materials", indent=15)
    draw_text("n. Moving Furniture at Tenant's Request ........ $12.00 per hour per person", indent=15)
    draw_text("o. Security Deposit as last month's rent ....... $100.00 bookkeeping charge", indent=15)
    space(0.3)

    check_page(2)

    draw_text("p. Fee Schedule for Cancellation of lease prior to Move-In:", indent=15)
    draw_text("   1. Over 60 days prior to Move-In ............ Forfeiture of Security Deposit", indent=15)
    draw_text("   2. Within 60 days of Move-In ................ No cancellation; Liable for rent", indent=15)
    draw_text("      until apartment re-rented", indent=15)
    space(0.3)
    draw_text("q. Forfeiture of deposit if you sublet ......... Liable for rent until re-rented", indent=15)
    space(0.5)

    # ==================== SECTION 37: SEVERABILITY ====================
    draw_text("37. SEVERABILITY.", bold=True)
    draw_wrapped("In case any one or more of the provisions contained in this lease shall for any reason be held to be invalid, illegal, or unenforceable in any respect, such invalidity, illegality, or unenforceability shall not affect any other provision thereof and this lease shall be construed as if such invalid, illegal, or unenforceable provision had never been contained herein.", indent=0)
    space(1)

    check_page(3)

    # ==================== VEHICLE INFORMATION ====================
    draw_text("VEHICLE INFORMATION", bold=True)
    space(0.5)
    for i in range(1, num_tenants + 1):
        draw_text(f"Tenant {i} Vehicle:")
        draw_text(f"Color: _____________ Make: _________________ Model: _________________")
        draw_text(f"License Plate: _________________ State: _______")
        space(0.5)

    check_page(3)

    # ==================== SIGNATURES ====================
    draw_text("SIGNATURES", bold=True)
    space(0.3)
    draw_wrapped("The undersigned Lessee(s) acknowledge that they have read this Lease, understand its terms, and agree to be bound by its provisions. Each Lessee acknowledges receipt of a copy of this Lease. The name and address of the owner of Victorian Village Apartments is Jim/Jolinda Edwards, P.O. Box 471, Nelsonville, Ohio 45764.", indent=0)
    space(0.5)
    draw_text("IN WITNESS WHEREOF, the Lessor and the Lessee(s) have executed these presents,")
    draw_text("the day and year first above written.")
    space(1)

    # Lessor signature
    draw_text("LESSOR:")
    space(0.5)
    draw_text("Signature: _________________________________  Date: _______________")
    space(0.5)
    draw_text("Print Name: Jim and Jolinda Edwards, d/b/a Victorian Village Apartments")
    space(1.2)

    # Lessee signatures
    draw_text("LESSEE(S):")
    space(0.5)

    for i in range(1, num_tenants + 1):
        check_page(1.5)
        draw_text(f"Tenant {i} Signature: _________________________________  Date: _______________")
        space(0.5)
        draw_text(f"Print Name: _________________________________")
        space(1)

    c.save()
    print(f"Created: {filename}")
    return filename


def main():
    """Generate all 4 lease versions."""
    print("Generating Victorian Village Lease PDFs...")
    print("=" * 50)

    for num in [1, 2, 3, 4]:
        create_lease_pdf(num)

    print("=" * 50)
    print("Done! Files ready for Innago field placement.")
    print("\nFont: Helvetica (use Arial in Innago text boxes)")
    print("Sizes: 14pt titles, 11pt headings, 10pt body")


if __name__ == "__main__":
    main()
