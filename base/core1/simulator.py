import numpy as np
import json
import time
from scipy.integrate import solve_ivp
import threading
import asyncio
import math

class BatteryThermalSimulator:
    def __init__(self, params, callback=None):
        # Initialize with parameters from the model
        self.params = params
        self.callback = callback
        
        # Convert dimensions to meters for calculations
        self.radius = params.cell_radius / 1000.0  # m
        self.height = params.cell_height / 1000.0  # m
        
        # Thermal properties
        self.k = params.thermal_conductivity  # W/m·K
        self.cp = params.specific_heat_capacity  # J/kg·K
        self.rho = params.density  # kg/m³
        
        # Initial conditions
        self.T_init = params.initial_temperature  # °C
        self.T_amb = params.ambient_temperature  # °C
        
        # Electrical properties
        self.capacity = params.nominal_capacity / 1000.0  # Ah
        self.voltage = params.nominal_voltage  # V
        self.resistance = params.internal_resistance  # Ω
        
        # Simulation settings
        self.dt = params.time_step  # seconds
        self.max_time = params.max_simulation_time  # seconds
        
        # Current profile
        self.current_profile = json.loads(params.current_profile)
        self.current_profile = {float(k): float(v) for k, v in self.current_profile.items()}
        
        # Create spatial discretization
        self.nr = 10  # Number of radial nodes
        self.nz = 20  # Number of axial nodes
        self.mesh_r = np.linspace(0, self.radius, self.nr)
        self.mesh_z = np.linspace(0, self.height, self.nz)
        
        # Initialize temperature field (T_init everywhere)
        self.T = np.ones((self.nr, self.nz)) * self.T_init
        
        # Initialize time and current
        self.current_time = 0.0
        self.current = self.get_current(0.0)
        
        # Status
        self.running = False
        self.paused = False
    
    def get_current(self, t):
        """Get current at time t by interpolating between points in the current profile"""
        times = sorted(list(self.current_profile.keys()))
        
        if t <= times[0]:
            return self.current_profile[times[0]]
        
        if t >= times[-1]:
            return self.current_profile[times[-1]]
        
        # Find the two times that bracket t
        for i in range(len(times) - 1):
            if times[i] <= t < times[i + 1]:
                t1, t2 = times[i], times[i + 1]
                i1, i2 = self.current_profile[t1], self.current_profile[t2]
                # Linear interpolation
                return i1 + (i2 - i1) * (t - t1) / (t2 - t1)
    
    def calculate_heat_generation(self, current):
        """Calculate heat generation based on current and internal resistance"""
        # Joule heating: P = I²R
        joule_heat = current**2 * self.resistance
        
        # Simplified heat distribution (concentrated at the core)
        heat_density = np.zeros((self.nr, self.nz))
        
        # Distribute heat generation across the cell (simplified as concentrated in the center)
        heat_density[0:self.nr//3, :] = joule_heat / (math.pi * (self.radius/3)**2 * self.height)
        
        return heat_density
    
    def update_temperature(self):
        """Update temperature field using finite difference method"""
        # Previous temperature field
        T_prev = self.T.copy()
        
        # Current heat generation
        q = self.calculate_heat_generation(self.current)
        
        # Thermal diffusivity
        alpha = self.k / (self.rho * self.cp)
        
        # New temperature field
        T_new = np.zeros_like(self.T)
        
        # Finite difference method (simplified 2D radial-axial heat equation)
        for i in range(1, self.nr - 1):
            r = self.mesh_r[i]
            dr = self.mesh_r[1] - self.mesh_r[0]
            
            for j in range(1, self.nz - 1):
                dz = self.mesh_z[1] - self.mesh_z[0]
                
                # Radial component (including cylindrical term)
                d2T_dr2 = (T_prev[i+1, j] - 2*T_prev[i, j] + T_prev[i-1, j]) / dr**2
                dT_dr = (T_prev[i+1, j] - T_prev[i-1, j]) / (2*dr)
                
                # Axial component
                d2T_dz2 = (T_prev[i, j+1] - 2*T_prev[i, j] + T_prev[i, j-1]) / dz**2
                
                # Heat equation in cylindrical coordinates
                dT_dt = alpha * (d2T_dr2 + dT_dr/r + d2T_dz2) + q[i, j] / (self.rho * self.cp)
                
                # Update temperature
                T_new[i, j] = T_prev[i, j] + dT_dt * self.dt
        
        # Boundary conditions (simplified)
        # Center axis (r=0) - symmetry
        T_new[0, :] = T_new[1, :]
        
        # Outer surface (r=R) - convective cooling
        h = 10.0  # Convective heat transfer coefficient (W/m²·K)
        T_new[-1, :] = T_new[-2, :] - dr * h / self.k * (T_new[-2, :] - self.T_amb)
        
        # Top and bottom - convective cooling
        T_new[:, 0] = T_new[:, 1] - dz * h / self.k * (T_new[:, 1] - self.T_amb)
        T_new[:, -1] = T_new[:, -2] - dz * h / self.k * (T_new[:, -2] - self.T_amb)
        
        self.T = T_new
    
    def get_temperature_data(self):
        """Get temperature data for visualization"""
        # Temperature at different key points
        center_temp = self.T[0, self.nz//2]
        surface_temp = self.T[-1, self.nz//2]
        top_temp = self.T[self.nr//2, -1]
        bottom_temp = self.T[self.nr//2, 0]
        
        # Get the full temperature field for color mapping
        # Convert to a more compact format for transmission
        temp_field = self.T.tolist()
        
        return {
            'time': self.current_time,
            'current': self.current,
            'center_temp': center_temp,
            'surface_temp': surface_temp,
            'top_temp': top_temp,
            'bottom_temp': bottom_temp,
            'temp_field': temp_field,
            'min_temp': np.min(self.T),
            'max_temp': np.max(self.T)
        }
    
    def run_simulation(self):
        """Run the simulation"""
        self.running = True
        
        while self.running and self.current_time < self.max_time:
            if not self.paused:
                # Update current based on time
                self.current = self.get_current(self.current_time)
                
                # Update temperature
                self.update_temperature()
                
                # Update time
                self.current_time += self.dt
                
                # Send data through callback
                if self.callback:
                    data = self.get_temperature_data()
                    self.callback(data)
                
                # Small delay to reduce CPU usage
                time.sleep(0.1)  # Adjust based on desired real-time speed
        
        self.running = False
    
    def start(self):
        """Start the simulation in a separate thread"""
        sim_thread = threading.Thread(target=self.run_simulation)
        sim_thread.daemon = True
        sim_thread.start()
    
    def pause(self):
        """Pause the simulation"""
        self.paused = True
    
    def resume(self):
        """Resume the simulation"""
        self.paused = False
    
    def stop(self):
        """Stop the simulation"""
        self.running = False