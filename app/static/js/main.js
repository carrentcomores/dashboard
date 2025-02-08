// Flash message handling
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages after 5 seconds
    setTimeout(function() {
        const flashMessages = document.querySelectorAll('.flash');
        flashMessages.forEach(function(message) {
            message.style.display = 'none';
        });
    }, 5000);

    // Booking form validation
    const bookingForm = document.getElementById('booking-form');
    if (bookingForm) {
        bookingForm.addEventListener('submit', function(e) {
            const startDate = new Date(document.getElementById('start_date').value);
            const endDate = new Date(document.getElementById('end_date').value);
            
            if (startDate >= endDate) {
                e.preventDefault();
                alert('End date must be after start date');
            }
        });
    }

    // Date inputs - Set min date to today
    const dateInputs = document.querySelectorAll('input[type="date"]');
    const today = new Date().toISOString().split('T')[0];
    dateInputs.forEach(input => {
        input.min = today;
    });

    // Dynamic price calculation
    const calculatePrice = () => {
        const startDate = new Date(document.getElementById('start_date').value);
        const endDate = new Date(document.getElementById('end_date').value);
        const dailyRate = document.getElementById('daily_rate')?.value;
        
        if (startDate && endDate && dailyRate) {
            const days = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
            const totalPrice = days * parseFloat(dailyRate);
            
            if (totalPrice > 0) {
                document.getElementById('total_price').textContent = 
                    `Total Price: $${totalPrice.toFixed(2)}`;
            }
        }
    };

    // Add event listeners for date changes
    document.getElementById('start_date')?.addEventListener('change', calculatePrice);
    document.getElementById('end_date')?.addEventListener('change', calculatePrice);

    // Car search/filter functionality
    const searchCars = () => {
        const searchInput = document.getElementById('car-search').value.toLowerCase();
        const cars = document.querySelectorAll('.car-card');
        
        cars.forEach(car => {
            const carDetails = car.querySelector('.car-details').textContent.toLowerCase();
            if (carDetails.includes(searchInput)) {
                car.style.display = 'block';
            } else {
                car.style.display = 'none';
            }
        });
    };

    document.getElementById('car-search')?.addEventListener('input', searchCars);

    // Mobile menu toggle
    const menuToggle = document.getElementById('menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    
    menuToggle?.addEventListener('click', () => {
        navLinks.classList.toggle('show');
    });
});
