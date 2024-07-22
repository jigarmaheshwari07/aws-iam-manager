// JavaScript for form validation
(function () {
    'use strict';
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms)
        .forEach(function (form) {
            form.addEventListener('submit', function (event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });
})();

// Function to add role
function addRole(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        let input = document.getElementById('roles_input');
        let value = input.value.trim();
        if (value) {
            let rolesContainer = document.getElementById('roles_container');
            let roleBadge = document.createElement('div');
            roleBadge.className = 'bg-white text-orange-600 border border-orange-600 rounded-full px-3 py-1 flex items-center space-x-2';
            roleBadge.innerHTML = `<span>${value}</span><button type="button" class="text-orange-600 focus:outline-none" onclick="removeRole(this)">&times;</button><input type="hidden" name="roles_to_analyze[]" value="${value}">`;
            rolesContainer.appendChild(roleBadge);
            input.value = '';
        }
    }
}

// Function to remove role
function removeRole(button) {
    let roleBadge = button.parentNode;
    roleBadge.parentNode.removeChild(roleBadge);
}
