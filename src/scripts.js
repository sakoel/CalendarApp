document.addEventListener('DOMContentLoaded', async function () {
    const form = document.getElementById('eventForm');
    const calendarBtn = document.getElementById('calendarBtn');

    // Check for ?authenticated=true in the URL
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('authenticated') === 'true') {
        localStorage.setItem('authenticated', 'true');
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    function setToAddEventMode() {
        calendarBtn.textContent = "Add to Calendar";
        calendarBtn.disabled = false;
        calendarBtn.classList.remove('bg-gray-500', 'hover:bg-gray-600');
        calendarBtn.classList.add('bg-blue-500', 'hover:bg-blue-600');
        calendarBtn.type = "submit";
    }

    function setToAuthMode() {
        calendarBtn.textContent = "Authenticate with Google Calendar";
        calendarBtn.disabled = false;
        calendarBtn.classList.remove('bg-blue-500', 'hover:bg-blue-600');
        calendarBtn.classList.add('bg-gray-500', 'hover:bg-gray-600');
        calendarBtn.type = "button";
    }

    // Set button mode based on authentication
    if (localStorage.getItem('authenticated') === 'true') {
        setToAddEventMode();
    } else {
        setToAuthMode();
    }

    // Handle button click when not authenticated
    calendarBtn.addEventListener('click', function () {
        if (calendarBtn.type === "button") {
            window.location.href = "https://calendarapp-9jvu.onrender.com/api/authenticate";
        }
    });

    logoutBtn.addEventListener('click', function () {
        localStorage.removeItem('authenticated');
        setToAuthMode();
        fetch("https://calendarapp-9jvu.onrender.com/api/logout", { method: "POST" })
            .then(res => {
                // Redirect to frontend after logout
                window.location.href = "/";
            });
        form.reset();
    });

    // Handle form submission when authenticated
    form.addEventListener('submit', async (event) => {
        if (calendarBtn.type !== "submit") {
            event.preventDefault();
            return;
        }
        event.preventDefault();

        const imageInput = document.getElementById('imageUpload');
        const manualDateInput = document.getElementById('manualDate');
        const taskDescriptionInput = document.getElementById('taskDescription');
        const manualTimeInput = document.getElementById('manualTime');

        const imageFile = imageInput.files[0];
        const manualDate = manualDateInput.value;
        const taskDescription = taskDescriptionInput.value;
        const manualTime = manualTimeInput.value;

        const formData = new FormData();
        if (imageFile) {
            formData.append('image', imageFile);
        }

        formData.append('date', manualDate);
        formData.append('description', taskDescription);
        formData.append('time', manualTime);

        console.log(formData);
        try {
            const response = await fetch('https://calendarapp-9jvu.onrender.com/api/create_event', {
                method: 'POST',
                body: formData,
            });

            if (response.ok) {
                const data = await response.json();
                console.log('Success:', data);
                alert('Event added successfully!');
                form.reset();
                // Show success message
                const successMessage = document.getElementById('successMessage');
                successMessage.classList.remove('hidden');
            } else {
                console.error('Error:', response.status);
                alert('Error adding event: ' + response.statusText);
            }
        } catch (error) {
            console.error('Network error:', error);
            alert('Network error: ' + error.message);
        }
    });
}); 