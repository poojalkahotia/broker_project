# invapp/views/party_views.py

from django.shortcuts import render, get_object_or_404, redirect
from brokerapp.forms import PartyForm, BrokerForm, ItemForm
from brokerapp.models import HeadParty, Broker, HeadItem ,SaleMaster, SaleDetails ,PurchaseMaster, PurchaseDetails, DailyPage, JamaEntry, NaameEntry
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
import json
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from num2words import num2words
from django.utils import timezone
from django.db.models import Sum, F, FloatField, ExpressionWrapper
from django.utils.dateparse import parse_date
from django.http import HttpResponse

from io import BytesIO
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Daily Report", ln=1, align="C")
        self.ln(5)

    def table_side(self, title, entries, total, x_pos, max_rows):
        """Side table banane ke liye"""
        start_y = self.get_y()
        self.set_xy(x_pos, start_y)
        self.set_font("Arial", "B", 12)
        self.cell(90, 10, title, ln=1, align="L")

        # header
        self.set_x(x_pos)
        self.set_font("Arial", "B", 10)
        self.cell(20, 8, "No", 1, 0, "C")
        self.cell(40, 8, "Party", 1, 0, "C")
        self.cell(30, 8, "Amount", 1, 1, "C")

        # rows
        self.set_font("Arial", "", 10)
        for e in entries:
            self.set_x(x_pos)
            self.cell(20, 8, str(e.entry_no), 1, 0, "C")
            self.cell(40, 8, e.party.partyname, 1, 0)
            self.cell(30, 8, f"{e.amount:.2f}", 1, 1, "R")

        # padding blank rows
        extra_rows = max_rows - len(entries)
        for _ in range(extra_rows):
            self.set_x(x_pos)
            self.cell(20, 8, "", 1, 0, "C")
            self.cell(40, 8, "", 1, 0)
            self.cell(30, 8, "", 1, 1, "R")

        # total row
        self.set_x(x_pos)
        self.set_font("Arial", "B", 10)
        self.cell(60, 8, "Total", 1, 0, "R")
        self.cell(30, 8, f"{total:.2f}", 1, 1, "R")



# -----------------------
# Helpers
# -----------------------
def to_decimal(val, default=Decimal('0')):
    """Safe conversion to Decimal."""
    try:
        return Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return default




# -----------------------
# Views
# -----------------------
def sale_form(request, invno=None):
    """
    Render sale form. If invno provided, load sale and its details and pass sale_items_json for the client UI.
    """
    sale = None
    sale_items_json = "[]"
    today_date = date.today().strftime("%Y-%m-%d")

    if invno:
        sale = get_object_or_404(SaleMaster, invno=invno)
        details = SaleDetails.objects.filter(salemaster=sale)
        items_data = []
        for d in details:
            items_data.append({
                "item_id": d.item.pk,
                "item_name": d.item.item_name,
                "bora": float(d.bora),
                "bn": float(d.bn),
                "bnwt": float(d.bnwt),
                "bo": float(d.bo),
                "bowt": float(d.bowt),
                "totalbora": float(d.bn*d.bnwt + d.bo*d.bowt),
                "qty": float(d.qty),
                "rate": float(d.rate),
                "amt": float(d.amount),
                "partywt": float(d.partywt),
                "millwt": float(d.millwt),
                "diffwt": float(d.diffwt),
                "lotno": d.lotno or "",
            })
        sale_items_json = json.dumps(items_data)

    next_invno = SaleMaster.objects.aggregate(Max("invno"))['invno__max']
    next_invno = (next_invno + 1) if next_invno else 1

    context = {
        "sale": sale,
        "sale_items_json": sale_items_json,  # for JS
        "next_invno": next_invno,
        "today_date": today_date,
        "items": HeadItem.objects.all().order_by('item_name'),
        "parties": HeadParty.objects.all().order_by('partyname'),
        "brokers": Broker.objects.all().order_by('brokername'),
    }
    return render(request, "brokerapp/sale.html", context)

# ===================== SAVE SALE =====================
@transaction.atomic
def save_sale(request):
    """
    Save a new SaleMaster and its SaleDetails.
    Expects 'items_json' hidden input (JSON array) in POST containing line items.
    """
    if request.method != "POST":
        return redirect('sale_form_new')

    try:
        # ---------- Header fields ----------
        invdate_str = request.POST.get("invdate")
        invdate = datetime.strptime(invdate_str, "%Y-%m-%d").date() if invdate_str else date.today()
        awakno = request.POST.get("awakno", "").strip()
        extra = request.POST.get("extra", "").strip()
        party_pk = request.POST.get("party")
        broker_pk = request.POST.get("broker")
        vehicleno = request.POST.get("vehicleno", "").strip()

        # ---------- Items JSON ----------
        items_json = request.POST.get("items_json") or "[]"
        items = json.loads(items_json)

        if not items:
            messages.error(request, "Add at least one item before saving.")
            return redirect("sale_form_new")

        # ---------- Totals ----------
        total_amt = Decimal('0')
        for it in items:
            total_amt += to_decimal(it.get("amt", 0))

        # ---------- Summary ----------
        batavpercent = to_decimal(request.POST.get("batavpercent", 0))
        batavamt = (total_amt * batavpercent / Decimal('100')).quantize(Decimal('0.01'))

        dr = to_decimal(request.POST.get("dr", 0))
        dramt = (total_amt * dr / Decimal('100')).quantize(Decimal('0.01'))

        qi = to_decimal(request.POST.get("qi", 0))
        other = to_decimal(request.POST.get("other", 0))
        advance = to_decimal(request.POST.get("advance", 0))
        total = (total_amt - batavamt - dramt - qi - other).quantize(Decimal('0.01'))
        netamt = (total - advance).quantize(Decimal('0.01'))

        # ---------- Resolve FKs ----------
        party = get_object_or_404(HeadParty, pk=party_pk)
        broker = get_object_or_404(Broker, pk=broker_pk)

        # ---------- Create SaleMaster ----------
        sale = SaleMaster.objects.create(
            invdate=invdate,
            awakno=awakno,
            party=party,
            broker=broker,
            vehicleno=vehicleno,
            extra=extra,
            totalamt=total_amt.quantize(Decimal('0.01')),
            batavpercent=batavpercent,
            batavamt=batavamt,
            dr=dr,
            dramt=dramt,
            qi=qi,
            other=other,
            total=total,
            advance=advance,
            netamt=netamt,
            remark=request.POST.get("remark", "").strip(),
        )

        # ---------- Create SaleDetails ----------
        for it in items:
            item_id = it.get("item_id")
            item_obj = get_object_or_404(HeadItem, pk=item_id)
            SaleDetails.objects.create(
                salemaster=sale,
                item=item_obj,
                bora=to_decimal(it.get("bora", 0)),
                bn=to_decimal(it.get("bn", 0)),
                bnwt=to_decimal(it.get("bnwt", 0)),
                bo=to_decimal(it.get("bo", 0)),
                bowt=to_decimal(it.get("bowt", 0)),
                qty=to_decimal(it.get("qty", 0)),
                rate=to_decimal(it.get("rate", 0)),
                amount=to_decimal(it.get("amt", 0)),
                partywt=to_decimal(it.get("partywt", 0)),
                millwt=to_decimal(it.get("millwt", 0)),
                diffwt=to_decimal(it.get("diffwt", 0)),
                lotno=it.get("lotno", "").strip(),
            )

        messages.success(request, "Sale entry saved successfully!")
        return redirect("saledata")

    except Exception as e:
        messages.error(request, f"Error saving sale: {e}")
        return redirect("sale_form_new")


@transaction.atomic
def update_sale(request, invno):
    """
    Update existing SaleMaster identified by invno. Replaces details with posted items.
    """
    sale = get_object_or_404(SaleMaster, invno=invno)

    if request.method != "POST":
        return redirect('sale_form_update', invno=invno)

    try:
        # ---------- Header fields ----------
        invdate_str = request.POST.get("invdate")
        invdate = datetime.strptime(invdate_str, "%Y-%m-%d").date() if invdate_str else sale.invdate
        awakno = request.POST.get("awakno", "").strip()
        party_pk = request.POST.get("party")
        broker_pk = request.POST.get("broker")
        vehicleno = request.POST.get("vehicleno", "").strip()
        extra = request.POST.get("extra", "").strip()

        # ---------- Line items JSON ----------
        items_json = request.POST.get("items_json") or "[]"
        items = json.loads(items_json)

        if not items:
            messages.error(request, "Add at least one item before saving.")
            return redirect("sale_form_update", invno=invno)

        # ---------- Calculate totals ----------
        total_amt = Decimal('0')
        for it in items:
            total_amt += to_decimal(it.get("amt", 0))

        # ---------- Summary ----------
        batavpercent = to_decimal(request.POST.get("batavpercent", 0))
        batavamt = (total_amt * batavpercent / Decimal('100')).quantize(Decimal('0.01'))

        dr = to_decimal(request.POST.get("dr", 0))
        dramt = (total_amt * dr / Decimal('100')).quantize(Decimal('0.01'))

        qi = to_decimal(request.POST.get("qi", 0))
        other = to_decimal(request.POST.get("other", 0))
        advance = to_decimal(request.POST.get("advance", 0))
        total = (total_amt - batavamt - dramt - qi - other).quantize(Decimal('0.01'))
        netamt = (total - advance).quantize(Decimal('0.01'))

        # ---------- Resolve Foreign Keys ----------
        party = get_object_or_404(HeadParty, pk=party_pk)
        broker = get_object_or_404(Broker, pk=broker_pk)

        # ---------- Update SaleMaster ----------
        sale.invdate = invdate
        sale.awakno = awakno
        sale.party = party
        sale.broker = broker
        sale.vehicleno = vehicleno
        sale.extra = extra
        sale.totalamt = total_amt.quantize(Decimal('0.01'))
        sale.batavpercent = batavpercent
        sale.batavamt = batavamt
        sale.dr = dr
        sale.dramt = dramt
        sale.qi = qi
        sale.other = other
        sale.advance = advance
        sale.total = total
        sale.netamt = netamt
        sale.remark = request.POST.get("remark", "").strip()
        sale.save()

        # ---------- Replace SaleDetails ----------
        SaleDetails.objects.filter(salemaster=sale).delete()
        for it in items:
            item_id = it.get("item_id")
            item_obj = get_object_or_404(HeadItem, pk=item_id)

            SaleDetails.objects.create(
                salemaster=sale,
                item=item_obj,
                bora=to_decimal(it.get("bora", 0)),
                bn=to_decimal(it.get("bn", 0)),
                bnwt=to_decimal(it.get("bnwt", 0)),
                bo=to_decimal(it.get("bo", 0)),
                bowt=to_decimal(it.get("bowt", 0)),
                qty=to_decimal(it.get("qty", 0)),
                rate=to_decimal(it.get("rate", 0)),
                amount=to_decimal(it.get("amt", 0)),
                partywt=to_decimal(it.get("partywt", 0)),
                millwt=to_decimal(it.get("millwt", 0)),
                diffwt=to_decimal(it.get("diffwt", 0)),
                lotno=it.get("lotno", "").strip(),
            )

        messages.success(request, "Sale entry updated successfully!")
        return redirect("saledata")

    except Exception as e:
        messages.error(request, f"Error updating sale: {e}")
        return redirect("sale_form_update", invno=invno)

def sale_data_view(request):
    """List of sales for viewing in a table (saledata)."""
    sales = SaleMaster.objects.all().order_by("-invno")
    return render(request, "brokerapp/saledata.html", {
        "sales": sales,
        "today_date": date.today(),
    })


def delete_sale(request, invno):
    sale = get_object_or_404(SaleMaster, invno=invno)
    sale.delete()
    messages.success(request, "Sale entry deleted successfully!")
    return redirect("saledata")

def sale_report(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    broker_id = request.GET.get("broker")
    report_type = request.GET.get("report_type", "date")

    # Default date = today
    if not start_date:
        start_date = date.today().strftime("%Y-%m-%d")
    if not end_date:
        end_date = date.today().strftime("%Y-%m-%d")

    # Base queryset
    sales = SaleMaster.objects.all()
    if start_date:
        sales = sales.filter(invdate__gte=parse_date(start_date))
    if end_date:
        sales = sales.filter(invdate__lte=parse_date(end_date))
    if broker_id and broker_id != "all":
        sales = sales.filter(broker__brokername=broker_id)

    sales = sales.order_by("invdate")

    report_data = []

    # --- Grouping & Aggregates ---
    if report_type == "date":
        grouped = sales.values("invdate").annotate(
            total_totalamt=Sum("totalamt"),
            total_batavamt=Sum("batavamt"),
            total_dramt=Sum("dramt"),
            total_other=Sum("other"),
            total_total=Sum("total"),
            total_advance=Sum("advance"),
            total_netamt=Sum("netamt"),
        ).order_by("invdate")

        for g in grouped:
            group_sales = sales.filter(invdate=g["invdate"])
            report_data.append({
                "group": g["invdate"],
                "items": group_sales,
                "totals": g
            })

    elif report_type == "broker":
        grouped = sales.values("invdate", "broker__brokername").annotate(
            total_totalamt=Sum("totalamt"),
            total_batavamt=Sum("batavamt"),
            total_dramt=Sum("dramt"),
            total_other=Sum("other"),
            total_total=Sum("total"),
            total_advance=Sum("advance"),
            total_netamt=Sum("netamt"),
        ).order_by("invdate", "broker__brokername")

        for g in grouped:
            group_sales = sales.filter(
                invdate=g["invdate"],
                broker__brokername=g["broker__brokername"]
            )
            report_data.append({
                "group": f"{g['invdate']} - {g['broker__brokername'] or 'No Broker'}",
                "items": group_sales,
                "totals": g
            })

    # Overall Totals
    overall_totals = sales.aggregate(
        total_totalamt=Sum("totalamt"),
        total_batavamt=Sum("batavamt"),
        total_dramt=Sum("dramt"),
        total_other=Sum("other"),
        total_total=Sum("total"),
        total_advance=Sum("advance"),
        total_netamt=Sum("netamt"),
    )

    brokers = Broker.objects.all()

    context = {
        "report_data": report_data,
        "overall_totals": overall_totals,
        "start_date": start_date,
        "end_date": end_date,
        "brokers": brokers,
        "selected_broker": broker_id if broker_id != "all" else None,
        "report_type": report_type,
    }

    return render(request, "brokerapp/sale_report.html", context)

def bardana_report(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    party_id = request.GET.get("party")
    broker_id = request.GET.get("broker")
    report_type = request.GET.get("report_type", "date")  # date / party / broker

    # Default date = today
    if not start_date:
        start_date = date.today().strftime("%Y-%m-%d")
    if not end_date:
        end_date = date.today().strftime("%Y-%m-%d")

    # Base queryset
    details = (
        SaleDetails.objects
        .select_related('salemaster', 'item', 'salemaster__party', 'salemaster__broker')
        .filter(
            salemaster__invdate__gte=parse_date(start_date),
            salemaster__invdate__lte=parse_date(end_date)
        )
        .order_by('salemaster__invdate')
    )

    # Party / Broker filter
    if party_id and party_id != "all":
        details = details.filter(salemaster__party__pk=party_id)
    if broker_id and broker_id != "all":
        details = details.filter(salemaster__broker__pk=broker_id)

    # Prepare grouped data
    report_data = []

    if report_type == "date":
        group_values = details.values_list('salemaster__invdate', flat=True).distinct()
        for g in group_values:
            group_details = details.filter(salemaster__invdate=g)
            totals = group_details.aggregate(total_bn=Sum('bn'), total_bo=Sum('bo'))
            report_data.append({
                "group": g.strftime("%d-%m-%Y"),
                "items": group_details,
                "total_bn": totals["total_bn"] or 0,
                "total_bo": totals["total_bo"] or 0,
            })

    elif report_type == "party":
        group_values = details.values_list('salemaster__party__partyname', flat=True).distinct()
        for g in group_values:
            group_details = details.filter(salemaster__party__partyname=g)
            totals = group_details.aggregate(total_bn=Sum('bn'), total_bo=Sum('bo'))
            report_data.append({
                "group": g,
                "items": group_details,
                "total_bn": totals["total_bn"] or 0,
                "total_bo": totals["total_bo"] or 0,
            })

    elif report_type == "broker":
        group_values = details.values_list('salemaster__broker__brokername', flat=True).distinct()
        for g in group_values:
            group_details = details.filter(salemaster__broker__brokername=g)
            totals = group_details.aggregate(total_bn=Sum('bn'), total_bo=Sum('bo'))
            report_data.append({
                "group": g,
                "items": group_details,
                "total_bn": totals["total_bn"] or 0,
                "total_bo": totals["total_bo"] or 0,
            })

    # Fetch dropdown lists
    parties = HeadParty.objects.all()
    brokers = Broker.objects.all()

    context = {
        "report_data": report_data,
        "parties": parties,
        "brokers": brokers,
        "start_date": start_date,
        "end_date": end_date,
        "selected_party": party_id if party_id != "all" else None,
        "selected_broker": broker_id if broker_id != "all" else None,
        "report_type": report_type,
    }

    return render(request, "brokerapp/bardana_report.html", context)

def purchase_form(request, invno=None):
    """
    Render purchase form. If invno provided, load purchase and its details and pass purchase_items_json for the client UI.
    """
    purchase = None
    purchase_items_json = "[]"
    today_date = date.today().strftime("%Y-%m-%d")

    if invno:
        purchase = get_object_or_404(PurchaseMaster, invno=invno)
        details = PurchaseDetails.objects.filter(purchasemaster=purchase)
        items_data = []
        for d in details:
            items_data.append({
                "item_id": d.item.pk,
                "item_name": d.item.item_name,
                "bora": float(d.bora),
                "bn": float(d.bn),
                "bnwt": float(d.bnwt),
                "bo": float(d.bo),
                "bowt": float(d.bowt),
                "totalbora": float(d.bn*d.bnwt + d.bo*d.bowt),
                "qty": float(d.qty),
                "rate": float(d.rate),
                "amt": float(d.amount),
                "partywt": float(d.partywt),
                "millwt": float(d.millwt),
                "diffwt": float(d.diffwt),
                "lotno": d.lotno or "",
            })
        purchase_items_json = json.dumps(items_data)

    next_invno = PurchaseMaster.objects.aggregate(Max("invno"))['invno__max']
    next_invno = (next_invno + 1) if next_invno else 1

    context = {
        "purchase": purchase,
        "purchase_items_json": purchase_items_json,  # for JS
        "next_invno": next_invno,
        "today_date": today_date,
        "items": HeadItem.objects.all().order_by('item_name'),
        "parties": HeadParty.objects.all().order_by('partyname'),
        "brokers": Broker.objects.all().order_by('brokername'),
    }
    return render(request, "brokerapp/purchase.html", context)


@transaction.atomic
def save_purchase(request):
    """
    Save a new PurchaseMaster and its PurchaseDetails.
    Expects 'items_json' hidden input (JSON array) in POST containing line items.
    """
    if request.method != "POST":
        return redirect('purchase_form_new')

    try:
        # ---------- Header fields ----------
        invdate_str = request.POST.get("invdate")
        invdate = datetime.strptime(invdate_str, "%Y-%m-%d").date() if invdate_str else date.today()
        awakno = request.POST.get("awakno", "").strip()
        extra = request.POST.get("extra", "").strip()
        party_pk = request.POST.get("party")
        broker_pk = request.POST.get("broker")
        vehicleno = request.POST.get("vehicleno", "").strip()

        # ---------- Items JSON ----------
        items_json = request.POST.get("items_json") or "[]"
        items = json.loads(items_json)

        if not items:
            messages.error(request, "Add at least one item before saving.")
            return redirect("purchase_form_new")

        # ---------- Totals ----------
        total_amt = Decimal('0')
        for it in items:
            total_amt += to_decimal(it.get("amt", 0))

        # ---------- Summary ----------
        batavpercent = to_decimal(request.POST.get("batavpercent", 0))
        batavamt = (total_amt * batavpercent / Decimal('100')).quantize(Decimal('0.01'))

        dr = to_decimal(request.POST.get("dr", 0))
        dramt = (total_amt * dr / Decimal('100')).quantize(Decimal('0.01'))

        qi = to_decimal(request.POST.get("qi", 0))
        other = to_decimal(request.POST.get("other", 0))
        advance = to_decimal(request.POST.get("advance", 0))
        total = (total_amt - batavamt - dramt - qi - other).quantize(Decimal('0.01'))
        netamt = (total - advance).quantize(Decimal('0.01'))

        # ---------- Resolve FKs ----------
        party = get_object_or_404(HeadParty, pk=party_pk)
        broker = get_object_or_404(Broker, pk=broker_pk)

        # ---------- Create PurchaseMaster ----------
        purchase = PurchaseMaster.objects.create(
            invdate=invdate,
            awakno=awakno,
            party=party,
            broker=broker,
            vehicleno=vehicleno,
            extra=extra,
            totalamt=total_amt.quantize(Decimal('0.01')),
            batavpercent=batavpercent,
            batavamt=batavamt,
            dr=dr,
            dramt=dramt,
            qi=qi,
            other=other,
            total=total,
            advance=advance,
            netamt=netamt,
            remark=request.POST.get("remark", "").strip(),
        )

        # ---------- Create PurchaseDetails ----------
        for it in items:
            item_id = it.get("item_id")
            item_obj = get_object_or_404(HeadItem, pk=item_id)
            PurchaseDetails.objects.create(
                purchasemaster=purchase,
                item=item_obj,
                bora=to_decimal(it.get("bora", 0)),
                bn=to_decimal(it.get("bn", 0)),
                bnwt=to_decimal(it.get("bnwt", 0)),
                bo=to_decimal(it.get("bo", 0)),
                bowt=to_decimal(it.get("bowt", 0)),
                qty=to_decimal(it.get("qty", 0)),
                rate=to_decimal(it.get("rate", 0)),
                amount=to_decimal(it.get("amt", 0)),
                partywt=to_decimal(it.get("partywt", 0)),
                millwt=to_decimal(it.get("millwt", 0)),
                diffwt=to_decimal(it.get("diffwt", 0)),
                lotno=it.get("lotno", "").strip(),
            )

        messages.success(request, "Purchase entry saved successfully!")
        return redirect("purchasedata")

    except Exception as e:
        messages.error(request, f"Error saving purchase: {e}")
        return redirect("purchase_form_new")


@transaction.atomic
def update_purchase(request, invno):
    """
    Update existing PurchaseMaster identified by invno. Replaces details with posted items.
    """
    purchase = get_object_or_404(PurchaseMaster, invno=invno)

    if request.method != "POST":
        return redirect('purchase_form_update', invno=invno)

    try:
        # ---------- Header fields ----------
        invdate_str = request.POST.get("invdate")
        invdate = datetime.strptime(invdate_str, "%Y-%m-%d").date() if invdate_str else purchase.invdate
        awakno = request.POST.get("awakno", "").strip()
        extra = request.POST.get("extra", "").strip()
        party_pk = request.POST.get("party")
        broker_pk = request.POST.get("broker")
        vehicleno = request.POST.get("vehicleno", "").strip()

        # ---------- Line items JSON ----------
        items_json = request.POST.get("items_json") or "[]"
        items = json.loads(items_json)

        if not items:
            messages.error(request, "Add at least one item before saving.")
            return redirect("purchase_form_update", invno=invno)

        # ---------- Calculate totals ----------
        total_amt = Decimal('0')
        for it in items:
            total_amt += to_decimal(it.get("amt", 0))

        # ---------- Summary ----------
        batavpercent = to_decimal(request.POST.get("batavpercent", 0))
        batavamt = (total_amt * batavpercent / Decimal('100')).quantize(Decimal('0.01'))

        dr = to_decimal(request.POST.get("dr", 0))
        dramt = (total_amt * dr / Decimal('100')).quantize(Decimal('0.01'))

        qi = to_decimal(request.POST.get("qi", 0))
        other = to_decimal(request.POST.get("other", 0))
        advance = to_decimal(request.POST.get("advance", 0))
        total = (total_amt - batavamt - dramt - qi - other).quantize(Decimal('0.01'))
        netamt = (total - advance).quantize(Decimal('0.01'))

        # ---------- Resolve Foreign Keys ----------
        party = get_object_or_404(HeadParty, pk=party_pk)
        broker = get_object_or_404(Broker, pk=broker_pk)

        # ---------- Update PurchaseMaster ----------
        purchase.invdate = invdate
        purchase.awakno = awakno
        purchase.extra = extra
        purchase.party = party
        purchase.broker = broker
        purchase.vehicleno = vehicleno
        purchase.totalamt = total_amt.quantize(Decimal('0.01'))
        purchase.batavpercent = batavpercent
        purchase.batavamt = batavamt
        purchase.dr = dr
        purchase.dramt = dramt
        purchase.qi = qi
        purchase.other = other
        purchase.total = total
        purchase.advance = advance
        purchase.netamt = netamt
        purchase.remark = request.POST.get("remark", "").strip()
        purchase.save()

        # ---------- Replace PurchaseDetails ----------
        PurchaseDetails.objects.filter(purchasemaster=purchase).delete()
        for it in items:
            item_id = it.get("item_id")
            item_obj = get_object_or_404(HeadItem, pk=item_id)
            PurchaseDetails.objects.create(
                purchasemaster=purchase,
                item=item_obj,
                bora=to_decimal(it.get("bora", 0)),
                bn=to_decimal(it.get("bn", 0)),
                bnwt=to_decimal(it.get("bnwt", 0)),
                bo=to_decimal(it.get("bo", 0)),
                bowt=to_decimal(it.get("bowt", 0)),
                qty=to_decimal(it.get("qty", 0)),
                rate=to_decimal(it.get("rate", 0)),
                amount=to_decimal(it.get("amt", 0)),
                partywt=to_decimal(it.get("partywt", 0)),
                millwt=to_decimal(it.get("millwt", 0)),
                diffwt=to_decimal(it.get("diffwt", 0)),
                lotno=it.get("lotno", "").strip(),
            )

        messages.success(request, "Purchase entry updated successfully!")
        return redirect("purchasedata")

    except Exception as e:
        messages.error(request, f"Error updating purchase: {e}")
        return redirect("purchase_form_update", invno=invno)

def purchase_data_view(request):
    """List of purchases for viewing in a table (purchasedata)."""
    purchases = PurchaseMaster.objects.all().order_by("-invno")
    return render(request, "brokerapp/purchasedata.html", {
        "purchases": purchases,
        "today_date": date.today(),
    })


def delete_purchase(request, invno):
    purchase = get_object_or_404(PurchaseMaster, invno=invno)
    purchase.delete()
    messages.success(request, "Purchase entry deleted successfully!")
    return redirect("purchasedata")

def purchase_report(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    broker_id = request.GET.get("broker")
    report_type = request.GET.get("report_type", "date")

    # Default date = today
    if not start_date:
        start_date = date.today().strftime("%Y-%m-%d")
    if not end_date:
        end_date = date.today().strftime("%Y-%m-%d")

    # Base queryset
    purchases = PurchaseMaster.objects.all()
    if start_date:
        purchases = purchases.filter(invdate__gte=parse_date(start_date))
    if end_date:
        purchases = purchases.filter(invdate__lte=parse_date(end_date))
    if broker_id and broker_id != "all":
        purchases = purchases.filter(broker__brokername=broker_id)

    purchases = purchases.order_by("invdate")

    report_data = []

    # --- Grouping & Aggregates ---
    if report_type == "date":
        grouped = purchases.values("invdate").annotate(
            total_totalamt=Sum("totalamt"),
            total_batavamt=Sum("batavamt"),
            total_dramt=Sum("dramt"),
            total_other=Sum("other"),
            total_total=Sum("total"),
            total_advance=Sum("advance"),
            total_netamt=Sum("netamt"),
        ).order_by("invdate")

        for g in grouped:
            group_purchases = purchases.filter(invdate=g["invdate"])
            report_data.append({
                "group": g["invdate"],
                "items": group_purchases,
                "totals": g
            })

    elif report_type == "broker":
        grouped = purchases.values("invdate", "broker__brokername").annotate(
            total_totalamt=Sum("totalamt"),
            total_batavamt=Sum("batavamt"),
            total_dramt=Sum("dramt"),
            total_other=Sum("other"),
            total_total=Sum("total"),
            total_advance=Sum("advance"),
            total_netamt=Sum("netamt"),
        ).order_by("invdate", "broker__brokername")

        for g in grouped:
            group_purchases = purchases.filter(
                invdate=g["invdate"],
                broker__brokername=g["broker__brokername"]
            )
            report_data.append({
                "group": f"{g['invdate']} - {g['broker__brokername'] or 'No Broker'}",
                "items": group_purchases,
                "totals": g
            })

    # Overall Totals
    overall_totals = purchases.aggregate(
        total_totalamt=Sum("totalamt"),
        total_batavamt=Sum("batavamt"),
        total_dramt=Sum("dramt"),
        total_other=Sum("other"),
        total_total=Sum("total"),
        total_advance=Sum("advance"),
        total_netamt=Sum("netamt"),
    )

    brokers = Broker.objects.all()

    context = {
        "report_data": report_data,
        "overall_totals": overall_totals,
        "start_date": start_date,
        "end_date": end_date,
        "brokers": brokers,
        "selected_broker": broker_id if broker_id != "all" else None,
        "report_type": report_type,
    }

    return render(request, "brokerapp/purchase_report.html", context)


def party_view(request, pk=None):
    instance = None
    if pk:
        instance = get_object_or_404(HeadParty, pk=pk)

    if request.method == 'POST':
        form = PartyForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            if pk:
                messages.success(request, '✅ Party updated successfully!')
            else:
                messages.success(request, '✅ Party added successfully!')
            return redirect('party')  # back to form list
    else:
        form = PartyForm(instance=instance)

    parties = HeadParty.objects.all()
    return render(request, 'brokerapp/party.html', {
        'form': form,
        'parties': parties,
        'editing': pk is not None,
        'editing_id': pk
    })


def party_delete(request, pk):
    party = get_object_or_404(HeadParty, pk=pk)
    party.delete()
    messages.success(request, "Party deleted successfully!")
    return redirect('party')

def broker_view(request, pk=None):
    instance = None
    if pk:
        instance = get_object_or_404(Broker, pk=pk)

    if request.method == 'POST':
        form = BrokerForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            if pk:
                messages.success(request, '✅ Broker updated successfully!')
            else:
                messages.success(request, '✅ Broker added successfully!')
            return redirect('broker')  # back to form list
    else:
        form = BrokerForm(instance=instance)

    brokers = Broker.objects.all()
    return render(request, 'brokerapp/broker.html', {
        'form': form,
        'brokers': brokers,
        'editing': pk is not None,
        'editing_id': pk
    })


# Delete Broker
def broker_delete(request, pk):
    broker = get_object_or_404(Broker, pk=pk)
    broker.delete()
    messages.success(request, "Broker deleted successfully!")
    return redirect('broker')

@login_required
def dashboard(request):
    return render(request, 'brokerapp/dashboard.html')

def item_view(request):
    selected_item = None
    items = HeadItem.objects.all()
    form = ItemForm()

    if request.method == 'POST':
        action = request.POST.get('action')
        item_name = request.POST.get('item_name')

        if item_name:
            try:
                selected_item = HeadItem.objects.get(item_name=item_name)
            except HeadItem.DoesNotExist:
                selected_item = None

        if action == 'save':
            form = ItemForm(request.POST, instance=selected_item)
            if form.is_valid():
                form.save()
                messages.success(request, "Item saved successfully!")
                return redirect('item')

        elif action == 'delete' and selected_item:
            selected_item.delete()
            messages.success(request, "Item deleted successfully!")
            return redirect('item')

    return render(request, 'brokerapp/item.html', {
        'form': form,
        'items': items,
    })


@require_GET
def daily_page_view(request):
    today = timezone.localdate().strftime("%Y-%m-%d")

    parties = HeadParty.objects.all().order_by('partyname')
    brokers = Broker.objects.all().order_by('brokername')  #
    # get today's page or None
    daily_page = DailyPage.objects.filter(date=today).first()
    jama_entries = daily_page.jama_entries.all() if daily_page else []
    naame_entries = daily_page.naame_entries.all() if daily_page else []
    context = {
        'today': today,
        'parties': parties,
        'brokers': brokers, 
        'jama_entries': jama_entries,
        'naame_entries': naame_entries,
    }
    return render(request, 'brokerapp/daily_page.html', context)

@require_GET
def daily_page_show(request):
    # expects ?date=YYYY-MM-DD
    d = request.GET.get('date')
    if not d:
        return JsonResponse({'error': 'date is required'}, status=400)
    try:
        date_obj = timezone.datetime.strptime(d, '%Y-%m-%d').date()
    except Exception:
        return JsonResponse({'error': 'invalid date format'}, status=400)

    daily_page = DailyPage.objects.filter(date=date_obj).first()
    jama = []
    naame = []
    if daily_page:
        jama = list(daily_page.jama_entries.values('entry_no','party__partyname','party','amount','remark','created_at'))
        naame = list(daily_page.naame_entries.values('entry_no','party__partyname','party','amount','remark','created_at'))

    return JsonResponse({'date': d, 'jama': jama, 'naame': naame})

@require_POST
def daily_page_jama_add(request):
    # expects form fields: date, party (id), broker (id), amount, remark
    date = request.POST.get('date')
    party_id = request.POST.get('party')
    broker_id = request.POST.get('broker')
    amount = request.POST.get('amount')
    remark = request.POST.get('remark', '')  # remark blank ho sakta hai

    # Basic validation
    if not (date and party_id and broker_id and amount):
        return JsonResponse({'error': 'Missing fields'}, status=400)

    try:
        date_obj = timezone.datetime.strptime(date, '%Y-%m-%d').date()
        amt = float(amount)
    except Exception:
        return JsonResponse({'error': 'Invalid input'}, status=400)

    # Fetch Party
    try:
        party = HeadParty.objects.get(pk=party_id)
    except HeadParty.DoesNotExist:
        return JsonResponse({'error': 'Party not found'}, status=404)

    # Fetch Broker
    try:
        broker = Broker.objects.get(pk=broker_id)
    except Broker.DoesNotExist:
        return JsonResponse({'error': 'Broker not found'}, status=404)

    # Create or update DailyPage and add entry
    with transaction.atomic():
        daily_page, _ = DailyPage.objects.get_or_create(date=date_obj)
        entry = JamaEntry.objects.create(
            daily_page=daily_page,
            party=party,
            broker=broker,
            amount=amt,
            remark=remark.strip() if remark else ""  # optional remark safe
        )

    data = {
        'entry_no': entry.entry_no,
        'party_name': party.partyname,
        'broker_name': broker.brokername,
        'amount': f"{entry.amount:.2f}",
        'remark': entry.remark,
    }
    return JsonResponse({'success': True, 'entry': data})


@require_POST
def daily_page_naame_add(request):
    # expects form fields: date, party (id), broker (id), amount, remark
    date = request.POST.get('date')
    party_id = request.POST.get('party')
    broker_id = request.POST.get('broker')
    amount = request.POST.get('amount')
    remark = request.POST.get('remark', '')  # remark optional

    # Basic validation
    if not (date and party_id and broker_id and amount):
        return JsonResponse({'error': 'Missing fields'}, status=400)

    try:
        date_obj = timezone.datetime.strptime(date, '%Y-%m-%d').date()
        amt = float(amount)
    except Exception:
        return JsonResponse({'error': 'Invalid input'}, status=400)

    # Fetch Party
    try:
        party = HeadParty.objects.get(pk=party_id)
    except HeadParty.DoesNotExist:
        return JsonResponse({'error': 'Party not found'}, status=404)

    # Fetch Broker
    try:
        broker = Broker.objects.get(pk=broker_id)
    except Broker.DoesNotExist:
        return JsonResponse({'error': 'Broker not found'}, status=404)

    # Create or update DailyPage and add entry
    with transaction.atomic():
        daily_page, _ = DailyPage.objects.get_or_create(date=date_obj)
        entry = NaameEntry.objects.create(
            daily_page=daily_page,
            party=party,
            broker=broker,
            amount=amt,
            remark=remark.strip() if remark else ""  # optional remark safe
        )

    data = {
        'entry_no': entry.entry_no,
        'party_name': party.partyname,
        'broker_name': broker.brokername,
        'amount': f"{entry.amount:.2f}",
        'remark': entry.remark,
    }
    return JsonResponse({'success': True, 'entry': data})

@require_POST
def daily_page_jama_delete(request, entry_no):
    entry = get_object_or_404(JamaEntry, entry_no=entry_no)
    entry.delete()
    return JsonResponse({'success': True, 'entry_no': entry_no})

@require_POST
def daily_page_naame_delete(request, entry_no):
    entry = get_object_or_404(NaameEntry, entry_no=entry_no)
    entry.delete()
    return JsonResponse({'success': True, 'entry_no': entry_no})

def daily_page_pdf(request):
    date = request.GET.get('date')
    if not date:
        return HttpResponse("Date not provided", status=400)

    # Get data
    jama_entries = JamaEntry.objects.filter(daily_page__date=date)
    naame_entries = NaameEntry.objects.filter(daily_page__date=date)

    total_jama = sum(j.amount for j in jama_entries)
    total_naame = sum(n.amount for n in naame_entries)
    diff = total_jama - total_naame

    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Daily Report - {date}", ln=True, align="C")
    pdf.ln(10)

    # --- Jama Table (Left Side) ---
    pdf.set_font("Arial", "B", 12)
    pdf.cell(90, 10, "Jama", ln=0, align="L")
    pdf.cell(90, 10, "Naame", ln=1, align="L")

    pdf.set_font("Arial", "B", 10)
    pdf.cell(10, 8, "No", border=1)
    pdf.cell(45, 8, "Party", border=1)
    pdf.cell(25, 8, "Amount", border=1, align="R")
    pdf.cell(10, 8, "", border=0)
    pdf.cell(10, 8, "No", border=1)
    pdf.cell(45, 8, "Party", border=1)
    pdf.cell(25, 8, "Amount", border=1, align="R")
    pdf.ln()

    pdf.set_font("Arial", "", 10)
    max_len = max(len(jama_entries), len(naame_entries))
    for i in range(max_len):
        if i < len(jama_entries):
            j = jama_entries[i]
            pdf.cell(10, 8, str(j.entry_no), border=1)
            pdf.cell(45, 8, j.party.partyname, border=1)
            pdf.cell(25, 8, f"{j.amount:.2f}", border=1, align="R")
        else:
            pdf.cell(80, 8, "", border=0)
        pdf.cell(10, 8, "", border=0)
        if i < len(naame_entries):
            n = naame_entries[i]
            pdf.cell(10, 8, str(n.entry_no), border=1)
            pdf.cell(45, 8, n.party.partyname, border=1)
            pdf.cell(25, 8, f"{n.amount:.2f}", border=1, align="R")
        else:
            pdf.cell(80, 8, "", border=0)
        pdf.ln()

    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(90, 8, f"Jama Total: {total_jama:.2f}", ln=0)
    pdf.cell(90, 8, f"Naame Total: {total_naame:.2f}", ln=1)
    pdf.ln(5)
    pdf.cell(0, 8, f"Difference (Jama - Naame): {diff:.2f}", ln=1, align="R")

    # --- Return response ---
    pdf_bytes = pdf.output(dest='S').encode('latin1')  # ✅ correct way
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="DailyReport_{date}.pdf"'
    return response

