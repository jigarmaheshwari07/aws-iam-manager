document.addEventListener('DOMContentLoaded', function() {
    // Add event listener to the actionButton
    document.getElementById('actionButton').addEventListener('click', function() {
        const dropdown = document.getElementById('actionDropdown');
        dropdown.classList.toggle('hidden');
    });

    // Optional: Close the dropdown when clicking outside of it
    document.addEventListener('click', function(event) {
        const dropdown = document.getElementById('actionDropdown');
        const button = document.getElementById('actionButton');
        if (!button.contains(event.target) && !dropdown.contains(event.target)) {
            dropdown.classList.add('hidden');
        }
    });
});