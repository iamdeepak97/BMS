
# Register your models here.
from django.contrib import admin
from .models import BatteryCell, SimulationResult

@admin.register(BatteryCell)
class BatteryCellAdmin(admin.ModelAdmin):
    list_display = ('cell_type', 'form_factor', 'nominal_voltage', 'capacity', 'energy_density')
    list_filter = ('cell_type', 'form_factor')
    search_fields = ('cell_type', 'form_factor')

@admin.register(SimulationResult)
class SimulationResultAdmin(admin.ModelAdmin):
    list_display = ('battery_cell', 'created_at', 'load_resistance', 'initial_soc', 'temperature')
    list_filter = ('battery_cell__cell_type', 'created_at')
    search_fields = ('battery_cell__cell_type',)