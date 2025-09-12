document.addEventListener('DOMContentLoaded', async function() {
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
      calendarBtn.addEventListener('click', function() {
        if (calendarBtn.type === "button") {
          window.location.href = "https://calendarapp-9jvu.onrender.com/api/authenticate";
        }
      });

      logoutBtn.addEventListener('click', function() {
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
      form.addEventListener('submit', async function(event) {
        event.preventDefault();

        const formData = new FormData(form);

        try {
          const response = await fetch('https://calendarapp-9jvu.onrender.com/api/create_event', {
            method: 'POST',
            body: formData,
          });

          const data = await response.json();

          if (!response.ok) {
            // Log error details to the console
            console.error('Create Event Error:', data.error || response.statusText);
            alert('Error adding event: ' + (data.error || response.statusText));
            return;
          }

          // Success
          console.log('Event created:', data);
          alert('Event created successfully!');
        } catch (err) {
          // Network or unexpected error
          console.error('Network or unexpected error:', err);
          alert('Network error: ' + err.message);
        }
      });
    });