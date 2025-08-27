from django.db import models

class BatteryCell(models.Model):
    """Model for battery cell specifications"""
    CELL_TYPES = [
        ('li_ion_phosphate', 'Li-ion Phosphate'),
        ('li_ion_cobalt', 'Li-ion Cobalt'),
        ('nimh', 'NiMH'),
        ('lead_acid', 'Lead Acid'),
    ]
    FORM_FACTORS = [
        ('cylindrical', 'Cylindrical'),
        ('prismatic', 'Prismatic'),
        ('pouch', 'Pouch'),
    ]
    
    cell_type = models.CharField(max_length=50, choices=CELL_TYPES)
    form_factor = models.CharField(max_length=20, choices=FORM_FACTORS)
    length = models.FloatField(help_text="Length in mm")
    diameter = models.FloatField(help_text="Diameter in mm", null=True, blank=True)
    height = models.FloatField(help_text="Height in mm", null=True, blank=True)
    width = models.FloatField(help_text="Width in mm", null=True, blank=True)
    volume = models.FloatField(help_text="Volume in cm³", null=True, blank=True)
    
    # Electrical properties
    nominal_voltage = models.FloatField(help_text="Nominal voltage in V")
    capacity = models.FloatField(help_text="Capacity in mAh")
    energy_density = models.FloatField(help_text="Energy density in Wh/kg")
    internal_resistance = models.FloatField(help_text="Internal resistance in mΩ")
    heat_resistance = models.FloatField(help_text="Thermal resistance in K/W")
    
    # Additional properties
    max_discharge_current = models.FloatField(help_text="Maximum discharge current in A")
    max_charge_current = models.FloatField(help_text="Maximum charge current in A")
    cycle_life = models.IntegerField(help_text="Expected cycle life")
    
    def __str__(self):
        return f"{self.get_cell_type_display()} - {self.get_form_factor_display()}"
    
    def calculate_volume(self):
        """Calculate the volume based on dimensions"""
        if self.form_factor == 'cylindrical':
            # π * r² * h
            return 3.14159 * (self.diameter/2)**2 * self.length / 1000  # Convert to cm³
        elif self.form_factor == 'prismatic' or self.form_factor == 'pouch':
            return self.length * self.width * self.height / 1000  # Convert to cm³
        return 0
    
    def save(self, *args, **kwargs):
        # Calculate volume before saving
        self.volume = self.calculate_volume()
        super().save(*args, **kwargs)

class SimulationResult(models.Model):
    """Model to store simulation results"""
    battery_cell = models.ForeignKey(BatteryCell, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Input parameters
    load_resistance = models.FloatField(help_text="Load resistance in Ω")
    initial_soc = models.FloatField(help_text="Initial state of charge (0-100%)")
    temperature = models.FloatField(help_text="Ambient temperature in °C")
    simulation_duration = models.IntegerField(help_text="Simulation duration in minutes")
    
    # Results data (stored as JSON strings)
    emf_data = models.JSONField(null=True)  # EMF over time
    terminal_voltage_data = models.JSONField(null=True)  # Terminal voltage over time
    current_data = models.JSONField(null=True)  # Current over time
    resistance_data = models.JSONField(null=True)  # Internal resistance over time
    soc_data = models.JSONField(null=True)  # State of charge over time
    temperature_data = models.JSONField(null=True)  # Cell temperature over time
    
    def __str__(self):
        return f"Simulation for {self.battery_cell} at {self.created_at}"
    


