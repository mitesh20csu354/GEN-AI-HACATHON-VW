import carla 
import pygame  # type: ignore 

pygame.init() 

# Set initial tire pressure 
tire_pressure = 32.0  # Fixed tire pressure 

def get_vehicle_parameters(vehicle): 
    velocity = vehicle.get_velocity() 
    control = vehicle.get_control() 

    parameters = { 
        "speed": (velocity.x**2 + velocity.y**2 + velocity.z**2)**0.5 * 3.6,  # m/s to km/h 
        "throttle": control.throttle, 
        "steering": control.steer, 
        "brake": control.brake, 
        "reverse": control.reverse, 
        "gear": control.gear, 
        "handbrake": control.hand_brake, 
        "tire_pressure": tire_pressure  # Fixed tire pressure 
    } 
    return parameters 

def display_vehicle_parameters(screen, font, vehicle_params): 
    box_width, box_height = 300, 160  
    box_x, box_y = 10, 10 

    pygame.draw.rect(screen, (50, 50, 50), (box_x, box_y, box_width, box_height)) 

    lines = [ 
        f"Speed: {vehicle_params['speed']:.2f} km/h", 
        f"Throttle: {vehicle_params['throttle']:.2f}", 
        f"Steering: {vehicle_params['steering']:.2f}", 
        f"Brake: {vehicle_params['brake']:.2f}", 
        f"Reverse: {vehicle_params['reverse']}", 
        f"Gear: {vehicle_params['gear']}", 
        f"Handbrake: {vehicle_params['handbrake']}", 
        f"Tire Pressure: {vehicle_params['tire_pressure']:.2f} psi"  
    ] 

    for i, line in enumerate(lines): 
        text = font.render(line, True, (255, 255, 255)) 
        screen.blit(text, (box_x + 10, box_y + 10 + i * 20)) 

def spawn_vehicle_at_location(client): 
    world = client.get_world() 
    blueprint_library = world.get_blueprint_library() 
    vehicle_bp = blueprint_library.filter('vehicle.audi.tt')[0] 
    spawn_point = carla.Transform(carla.Location(x=50, y=30, z=10), carla.Rotation(yaw=180)) 
    vehicle = world.spawn_actor(vehicle_bp, spawn_point) 
    print(f"Vehicle spawned at location: {spawn_point.location}") 
    return vehicle 

def attach_camera_to_vehicle(vehicle, world, view_mode): 
    spectator = world.get_spectator() 
    transform = vehicle.get_transform()
    
    if view_mode == 'rear':
        offset = carla.Location(x=-6, z=2.5)
        camera_rotation = transform.rotation
    elif view_mode == 'front':
        offset = carla.Location(x=6, z=2.5)
        camera_rotation = carla.Rotation(pitch=0, yaw=transform.rotation.yaw + 180)
    elif view_mode == 'right':
        offset = carla.Location(x=1.5, y=4.5, z=1.5)  # Adjusted for better visibility
        camera_rotation = carla.Rotation(pitch=2, yaw=transform.rotation.yaw + 90)
    elif view_mode == 'left':
        offset = carla.Location(x=1.5, y=-4.5, z=1.5)  # Adjusted for better visibility
        camera_rotation = carla.Rotation(pitch=2, yaw=transform.rotation.yaw - 90)
    
    camera_location = transform.location + transform.get_forward_vector() * offset.x + carla.Location(y=offset.y, z=offset.z)
    spectator.set_transform(carla.Transform(camera_location, camera_rotation))


def adjust_tire_pressure(amount):
    global tire_pressure
    tire_pressure = max(0.0, tire_pressure + amount)  # Prevent negative pressure

def main(): 
    client = carla.Client('localhost', 2000) 
    client.set_timeout(10.0) 

    vehicle = None 
    view_mode = 'rear'  # Default view mode

    try: 
        vehicle = spawn_vehicle_at_location(client) 
        screen = pygame.display.set_mode((300, 300)) 
        font = pygame.font.Font(None, 26) 
        clock = pygame.time.Clock() 
        world = client.get_world() 

        while True: 
            vehicle_params = get_vehicle_parameters(vehicle) 
            screen.fill((0, 0, 0)) 
            display_vehicle_parameters(screen, font, vehicle_params) 
            pygame.display.flip() 

            # Attach camera to vehicle
            attach_camera_to_vehicle(vehicle, world, view_mode) 

            # Control logic
            keys = pygame.key.get_pressed() 
            control = carla.VehicleControl() 

            # Control the vehicle
            if keys[pygame.K_w]:  # Forward 
                control.throttle = 1.0 
            if keys[pygame.K_r]:  # Reverse 
                control.reverse = True 
                control.throttle = 0.8 
            if keys[pygame.K_a]:  # Steer left 
                control.steer = -0.25 
            if keys[pygame.K_d]:  # Steer right 
                control.steer = 0.25 
            if keys[pygame.K_s]:  # Brake 
                control.brake = 0.5 
            if keys[pygame.K_SPACE]:  # Full Brake 
                control.brake = 1.0 
            if keys[pygame.K_h]:  # Handbrake 
                control.hand_brake = True 
            if keys[pygame.K_DOWN]:  # Decrease tire pressure 
                adjust_tire_pressure(-1.0)  # Decrease pressure by 1.0
                vehicle.set_location(vehicle.get_location() + carla.Location(z=-0.2))  # Simulate tilt effect

            # Simulate left tire puncture
            if keys[pygame.K_LEFT]:  # Puncture left tire
                vehicle.set_location(vehicle.get_location() + carla.Location(x=-0.2))  # Move to the left
                control.throttle = max(0, control.throttle - 0.9)  # Reduce speed

            # Change view mode

            if keys[pygame.K_e]:  # Right side view
                view_mode = 'right'
            elif keys[pygame.K_q]:  # Left side view
                view_mode = 'left'
            elif control.reverse:  # If reversing, show front view
                view_mode = 'front'
            else:  # Default to rear view
                view_mode = 'rear'

            vehicle.apply_control(control) 

            for event in pygame.event.get(): 
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): 
                    return 

            clock.tick(60)  # Cap the frame rate to 30 FPS 

    finally: 
        if vehicle is not None: 
            vehicle.destroy() 

if __name__ == '__main__': 
    main()
