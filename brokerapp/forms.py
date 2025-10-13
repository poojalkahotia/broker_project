from django import forms
from .models import HeadParty, Broker, HeadItem, SaleMaster, SaleDetails, PurchaseMaster, PurchaseDetails


class PartyForm(forms.ModelForm):
    class Meta:
        model = HeadParty
        fields = '__all__'
        widgets = {
            'partyname': forms.TextInput(attrs={'class': 'form-control',}),
            'add1': forms.TextInput(attrs={'class': 'form-control'}),
            'add2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'otherno': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'openingdebit': forms.NumberInput(attrs={'class': 'form-control'}),
            'openingcredit': forms.NumberInput(attrs={'class': 'form-control'}),

        }

    def __init__(self, *args, **kwargs):
        super(PartyForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].label = field.capitalize()

      # 👇 Disable 'partyname' if it's edit mode (instance exists)
        if self.instance and self.instance.pk:
            self.fields['partyname'].disabled = True

class BrokerForm(forms.ModelForm):
    class Meta:
        model = Broker
        fields = '__all__'
        widgets = {
            'brokername': forms.TextInput(attrs={'class': 'form-control'}),
            'mobileno': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'openingdebit': forms.NumberInput(attrs={'class': 'form-control'}),
            'openingcredit': forms.NumberInput(attrs={'class': 'form-control'}),
            'remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super(BrokerForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].label = field.capitalize()

        # 👇 Disable 'brokername' if it's edit mode
        if self.instance and self.instance.pk:
            self.fields['brokername'].disabled = True

class ItemForm(forms.ModelForm):
    class Meta:
        model = HeadItem
        fields = ['item_name']
        widgets = {
            'item_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        
        


# --------------------- SALE MASTER FORM ---------------------
class SaleMasterForm(forms.ModelForm):
    # Dropdowns (use same queryset), add classes consistent with bootstrap
    party = forms.ModelChoiceField(
        queryset=HeadParty.objects.all().order_by('partyname'),
        empty_label="Select Party",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    broker = forms.ModelChoiceField(
        queryset=Broker.objects.all().order_by('brokername'),
        empty_label="Select Broker",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = SaleMaster
        fields = [
            'invno', 'invdate', 'awakno',
            'party', 'broker', 'extra', 'vehicleno',
            'totalamt', 'batavpercent', 'batavamt',
            'dr', 'dramt', 'qi', 'other', 'total',
            'advance', 'netamt', 'remark'
        ]
        widgets = {
            'invno': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'invdate': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'awakno': forms.TextInput(attrs={'class': 'form-control'}),
            'extra': forms.TextInput(attrs={'class': 'form-control'}),   # new field
            'vehicleno': forms.TextInput(attrs={'class': 'form-control'}),
            'totalamt': forms.NumberInput(attrs={'class': 'form-control'}),
            'batavpercent': forms.NumberInput(attrs={'class': 'form-control'}),
            'batavamt': forms.NumberInput(attrs={'class': 'form-control'}),
            'dr': forms.NumberInput(attrs={'class': 'form-control'}),
            'dramt': forms.NumberInput(attrs={'class': 'form-control'}),
            'qi': forms.NumberInput(attrs={'class': 'form-control'}),
            'other': forms.NumberInput(attrs={'class': 'form-control'}),
            'total': forms.NumberInput(attrs={'class': 'form-control'}),
            'advance': forms.NumberInput(attrs={'class': 'form-control'}),
            'netamt': forms.NumberInput(attrs={'class': 'form-control'}),
            'remark': forms.TextInput(attrs={'class': 'form-control'}),  # single-line input
        }

    def clean(self):
        cleaned_data = super().clean()
        # keep basic validation here if needed; do not try to write to removed model fields
        return cleaned_data


class SaleDetailsForm(forms.ModelForm):
    item = forms.ModelChoiceField(
        queryset=HeadItem.objects.all().order_by('item_name'),
        empty_label="Select Item",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = SaleDetails
        fields = [
            'item', 'bora', 'bn', 'bnwt', 'bo', 'bowt',
            'qty', 'rate', 'amount', 'partywt', 'millwt', 'diffwt', 'lotno'
        ]
        widgets = {
            'bora': forms.NumberInput(attrs={'class': 'form-control'}),
            'bn': forms.NumberInput(attrs={'class': 'form-control'}),
            'bnwt': forms.NumberInput(attrs={'class': 'form-control'}),
            'bo': forms.NumberInput(attrs={'class': 'form-control'}),
            'bowt': forms.NumberInput(attrs={'class': 'form-control'}),
            'qty': forms.NumberInput(attrs={'class': 'form-control', 'oninput': 'calculateAmount()'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'oninput': 'calculateAmount()'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'partywt': forms.NumberInput(attrs={'class': 'form-control', 'oninput': 'calculateDiffWt()'}),
            'millwt': forms.NumberInput(attrs={'class': 'form-control', 'oninput': 'calculateDiffWt()'}),
            'diffwt': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'lotno': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        # if amount not provided by JS, compute from qty*rate
        qty = cleaned_data.get('qty') or 0
        rate = cleaned_data.get('rate') or 0
        amount = cleaned_data.get('amount')
        try:
            if (not amount or float(amount) == 0) and qty and rate:
                cleaned_data['amount'] = float(qty) * float(rate)
        except Exception:
            pass
        return cleaned_data
# --------------------- PURCHASE MASTER FORM ---------------------
# --------------------- PURCHASE MASTER FORM ---------------------
class PurchaseMasterForm(forms.ModelForm):
    # Dropdowns
    party = forms.ModelChoiceField(
        queryset=HeadParty.objects.all().order_by('partyname'),
        empty_label="Select Party",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    broker = forms.ModelChoiceField(
        queryset=Broker.objects.all().order_by('brokername'),
        empty_label="Select Broker",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = PurchaseMaster
        fields = [
            'invno', 'invdate', 'awakno',
            'party', 'broker', 'extra', 'vehicleno',
            'totalamt', 'batavpercent', 'batavamt',
            'dr', 'dramt', 'qi', 'other', 'total',
            'advance', 'netamt', 'remark'
        ]
        widgets = {
            'invno': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'invdate': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'awakno': forms.TextInput(attrs={'class': 'form-control'}),
            'extra': forms.TextInput(attrs={'class': 'form-control'}),   # new field
            'vehicleno': forms.TextInput(attrs={'class': 'form-control'}),
            'totalamt': forms.NumberInput(attrs={'class': 'form-control'}),
            'batavpercent': forms.NumberInput(attrs={'class': 'form-control'}),
            'batavamt': forms.NumberInput(attrs={'class': 'form-control'}),
            'dr': forms.NumberInput(attrs={'class': 'form-control'}),
            'dramt': forms.NumberInput(attrs={'class': 'form-control'}),
            'qi': forms.NumberInput(attrs={'class': 'form-control'}),     # new field
            'other': forms.NumberInput(attrs={'class': 'form-control'}),
            'total': forms.NumberInput(attrs={'class': 'form-control'}),
            'advance': forms.NumberInput(attrs={'class': 'form-control'}),
            'netamt': forms.NumberInput(attrs={'class': 'form-control'}),
            'remark': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        # Optional: you can calculate netamt etc. if needed
        return cleaned_data


# --------------------- PURCHASE DETAILS FORM ---------------------
class PurchaseDetailsForm(forms.ModelForm):
    item = forms.ModelChoiceField(
        queryset=HeadItem.objects.all().order_by('item_name'),
        empty_label="Select Item",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = PurchaseDetails
        fields = [
            'item', 'bora', 'bn', 'bnwt', 'bo', 'bowt',
            'qty', 'rate', 'amount', 'partywt', 'millwt', 'diffwt', 'lotno'
        ]
        widgets = {
            'bora': forms.NumberInput(attrs={'class': 'form-control'}),
            'bn': forms.NumberInput(attrs={'class': 'form-control'}),
            'bnwt': forms.NumberInput(attrs={'class': 'form-control'}),
            'bo': forms.NumberInput(attrs={'class': 'form-control'}),
            'bowt': forms.NumberInput(attrs={'class': 'form-control'}),
            'qty': forms.NumberInput(attrs={'class': 'form-control', 'oninput': 'calculateAmount()'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'oninput': 'calculateAmount()'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'partywt': forms.NumberInput(attrs={'class': 'form-control', 'oninput': 'calculateDiffWt()'}),
            'millwt': forms.NumberInput(attrs={'class': 'form-control', 'oninput': 'calculateDiffWt()'}),
            'diffwt': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'lotno': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        # if amount not provided by JS, compute from qty*rate
        qty = cleaned_data.get('qty') or 0
        rate = cleaned_data.get('rate') or 0
        amount = cleaned_data.get('amount')
        try:
            if (not amount or float(amount) == 0) and qty and rate:
                cleaned_data['amount'] = float(qty) * float(rate)
        except Exception:
            pass
        return cleaned_data
