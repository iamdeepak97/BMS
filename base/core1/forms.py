from django import forms
from .models import *

class BatteryCellSelectionForm(forms.Form):
    cell_type = forms.ChoiceField(
        choices=BatteryCell.CELL_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    form_factor = forms.ChoiceField(
        choices=BatteryCell.FORM_FACTORS,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class SimulationParametersForm(forms.ModelForm):
    class Meta:
        model = SimulationResult
        fields = ['load_resistance', 'initial_soc', 'temperature', 'simulation_duration']
        widgets = {
            'load_resistance': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.1', 'step': '0.1' ,'placeholder': '0.5Ω to 1.5Ω'}),
            'initial_soc': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '1'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'min': '-20', 'max': '60', 'step': '1'}),
            'simulation_duration': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '1440', 'step': '1'}),
        }



