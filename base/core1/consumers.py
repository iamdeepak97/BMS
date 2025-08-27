import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .simulator import BatteryThermalSimulator
from .models import SimulationParameters
import asyncio

class SimulationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.simulator = None
        self.sim_task = None
    
    async def disconnect(self, close_code):
        if self.simulator:
            self.simulator.stop()
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        command = data.get('command')
        
        if command == 'start_simulation':
            # Get parameters from request or use default
            param_id = data.get('param_id')
            
            if param_id:
                # Get parameters from database
                params = await self.get_parameters(param_id)
            else:
                # Create default parameters
                params = await self.create_parameters(data.get('parameters', {}))
            
            # Create simulator
            self.simulator = BatteryThermalSimulator(params, callback=self.send_update)
            
            # Start simulation
            self.simulator.start()
            
            # Send initial data
            await self.send(text_data=json.dumps({
                'type': 'simulation_started',
                'param_id': params.id
            }))
        
        elif command == 'pause_simulation':
            if self.simulator:
                self.simulator.pause()
                await self.send(text_data=json.dumps({
                    'type': 'simulation_paused'
                }))
        
        elif command == 'resume_simulation':
            if self.simulator:
                self.simulator.resume()
                await self.send(text_data=json.dumps({
                    'type': 'simulation_resumed'
                }))
        
        elif command == 'stop_simulation':
            if self.simulator:
                self.simulator.stop()
                self.simulator = None
                await self.send(text_data=json.dumps({
                    'type': 'simulation_stopped'
                }))
        
        elif command == 'update_parameters':
            # Update parameters and restart simulation
            params = await self.update_parameters(data.get('parameters', {}), data.get('param_id'))
            
            if self.simulator:
                self.simulator.stop()
            
            self.simulator = BatteryThermalSimulator(params, callback=self.send_update)
            self.simulator.start()
            
            await self.send(text_data=json.dumps({
                'type': 'parameters_updated',
                'param_id': params.id
            }))
    
    def send_update(self, data):
        """Callback function for the simulator to send updates"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def send_async():
            await self.send(text_data=json.dumps({
                'type': 'simulation_update',
                'data': data
            }))
        
        loop.run_until_complete(send_async())
        loop.close()
    
    async def get_parameters(self, param_id):
        """Get parameters from database"""
        from channels.db import database_sync_to_async
        
        @database_sync_to_async
        def get_param(param_id):
            return SimulationParameters.objects.get(id=param_id)
        
        return await get_param(param_id)
    
    async def create_parameters(self, params_data):
        """Create new parameters in database"""
        from channels.db import database_sync_to_async
        
        @database_sync_to_async
        def create_param(params_data):
            return SimulationParameters.objects.create(**params_data)
        
        return await create_param(params_data)
    
    async def update_parameters(self, params_data, param_id):
        """Update parameters in database"""
        from channels.db import database_sync_to_async
        
        @database_sync_to_async
        def update_param(params_data, param_id):
            params = SimulationParameters.objects.get(id=param_id)
            
            for key, value in params_data.items():
                setattr(params, key, value)
            
            params.save()
            return params
        
        return await update_param(params_data, param_id)