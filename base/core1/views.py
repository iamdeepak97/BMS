from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import BatteryCell, SimulationResult
from .forms import BatteryCellSelectionForm, SimulationParametersForm 
import json
import math
import numpy as np

def index(request):
    """Main view for the battery simulation app"""
    cell_form = BatteryCellSelectionForm()
    simulation_form = SimulationParametersForm()
    if request.method == 'POST':
        cell_form = BatteryCellSelectionForm(request.POST)
        simulation_form = SimulationParametersForm(request.POST)
        
        if cell_form.is_valid() and simulation_form.is_valid():
            # Get cell type from form
            cell_type = cell_form.cleaned_data['cell_type']
            form_factor = cell_form.cleaned_data['form_factor']
            # Get or create battery cell
            try:
                cell = BatteryCell.objects.get(cell_type=cell_type, form_factor=form_factor)
            except BatteryCell.DoesNotExist:
                # Create default cell if not exists
                if cell_type == 'li_ion_phosphate' and form_factor == 'cylindrical':
                    cell = BatteryCell(
                        cell_type=cell_type,
                        form_factor=form_factor,
                        length=65.0,
                        diameter=18.0,
                        nominal_voltage=3.2,
                        capacity=2500,
                        energy_density=120,
                        internal_resistance=25,
                        heat_resistance=10,
                        max_discharge_current=10,
                        max_charge_current=5,
                        cycle_life=2000
                    )
                    cell.save()
                else:
                    # Generic values for other cell types
                    cell = BatteryCell(
                        cell_type=cell_type,
                        form_factor=form_factor,
                        length=60.0,
                        diameter=18.0,
                        height=10.0,
                        width=30.0,
                        nominal_voltage=3.7,
                        capacity=2000,
                        energy_density=100,
                        internal_resistance=30,
                        heat_resistance=12,
                        max_discharge_current=8,
                        max_charge_current=4,
                        cycle_life=1500
                    )
                    cell.save()
            
            # Create simulation
            simulation = simulation_form.save(commit=False)
            simulation.battery_cell = cell

            # Run simulation
            run_battery_simulation(simulation)
            simulation.save()
            
            return redirect('simulation_results', simulation_id=simulation.id)
    
    return render(request, 'battery_app/index.html', {
        'cell_form': cell_form,
        'simulation_form': simulation_form,
    })

def simulation_results(request, simulation_id):
    """View for displaying simulation results"""
    simulation = SimulationResult.objects.get(id=simulation_id)
    
    return render(request, 'battery_app/simulation_results.html', {
        'simulation': simulation,
        'cell': simulation.battery_cell,
    })

def run_battery_simulation(simulation):
    """Run the battery simulation and populate the simulation object with results"""
    cell = simulation.battery_cell
    duration_minutes = simulation.simulation_duration
    load_resistance = simulation.load_resistance
    initial_soc = simulation.initial_soc / 100.0  # Convert percentage to decimal
    ambient_temp = simulation.temperature
    
    # Time array (minutes)
    time = np.linspace(0, duration_minutes, num=duration_minutes*6)  # 10-second intervals
    time_hours = time / 60.0
    
    # Battery parameters
    nominal_voltage = cell.nominal_voltage
    capacity_mah = cell.capacity
    capacity_ah = capacity_mah / 1000.0
    base_internal_resistance = cell.internal_resistance / 1000.0  # Convert from mΩ to Ω
    
    # SOC calculation
    # We'll simulate discharge at C/5 rate (discharge in 5 hours)
    c_rate = 0.2
    discharge_current = capacity_ah * c_rate
    
    # SOC decreases linearly for simplicity
    soc = initial_soc - (time_hours * c_rate / 5.0)
    soc = np.maximum(soc, 0.0)  # Ensure SOC doesn't go below 0
    
    # Internal resistance varies with SOC (simplified model)
    # Increases as SOC decreases
    internal_resistance = base_internal_resistance * (1 + 0.5 * (1 - soc))
    # EMF varies with SOC (simplified model for LiFePO4)
    # LiFePO4 has a relatively flat voltage curve
    emf = nominal_voltage * (0.9 + 0.2 * soc)
    
    # Terminal voltage with load
    terminal_voltage = emf - (discharge_current * internal_resistance)
    
    # Current calculation
    current = terminal_voltage / (load_resistance + internal_resistance)
    
    # Cell temperature calculation (simplified)
    # Heat generated = I^2 * R
    heat_generated = current**2 * internal_resistance
    temp_rise = heat_generated / cell.heat_resistance
    temperature = ambient_temp + temp_rise
    
    # Prepare data for JSON storage
    simulation.emf_data = json.dumps({
        'time': time.tolist(),
        'emf': emf.tolist()
    })
    
    simulation.terminal_voltage_data = json.dumps({
        'time': time.tolist(),
        'voltage': terminal_voltage.tolist()
    })
    
    simulation.current_data = json.dumps({
        'time': time.tolist(),
        'current': current.tolist()
    })
    
    simulation.resistance_data = json.dumps({
        'time': time.tolist(),
        'resistance': internal_resistance.tolist(),
        'soc': soc.tolist()
    })
    
    simulation.soc_data = json.dumps({
        'time': time.tolist(),
        'soc': (soc * 100).tolist()  # Convert back to percentage
    })
    
    simulation.temperature_data = json.dumps({
        'time': time.tolist(),
        'temperature': temperature.tolist()
    })
def get_cell_specs(request):
    """API endpoint to get cell specifications"""
    cell_type = request.GET.get('cell_type')
    form_factor = request.GET.get('form_factor')
    try:
        cell = BatteryCell.objects.get(cell_type=cell_type, form_factor=form_factor)
        return JsonResponse({
            'length': cell.length,
            'diameter': cell.diameter,
            'height': cell.height,
            'width': cell.width,
            'volume': cell.volume,
            'energy_density': cell.energy_density,
            'nominal_voltage': cell.nominal_voltage,
            'capacity': cell.capacity,
            'internal_resistance': cell.internal_resistance,
            'heat_resistance': cell.heat_resistance,
        })
    except BatteryCell.DoesNotExist:
        return JsonResponse({'error': 'Cell specifications not found'}, status=404)
