// Function to filter list items based on search input
function filterList(inputId, itemClass) {
    const input = document.getElementById(inputId);
    const filter = input.value.toLowerCase();
    const items = document.querySelectorAll(`.${itemClass}`);

    items.forEach(item => {
        const text = item.textContent || item.innerText;
        item.style.display = text.toLowerCase().includes(filter) ? '' : 'none';
    });
}

// Function to filter both roles and users within the "Trusted Users" section
function filterTrustedUsers() {
    const input = document.getElementById('trustedUserSearchInput');
    const filter = input.value.toLowerCase();
    const roles = document.querySelectorAll('.trusted-user-role');

    roles.forEach(role => {
        const roleTitle = role.querySelector('strong').textContent.toLowerCase();
        const users = role.querySelectorAll('.trusted-user-item');
        let roleVisible = false;

        users.forEach(user => {
            const userName = user.textContent.toLowerCase();
            if (userName.includes(filter) || roleTitle.includes(filter)) {
                user.style.display = '';
                roleVisible = true;
            } else {
                user.style.display = 'none';
            }
        });

        // Show the role if any nested user matches the filter, or if the role itself matches
        role.style.display = roleVisible ? '' : 'none';
    });
}

// Function to show role details
function showRoleDetails(roleName, element) {
    const accountId = element.dataset.accountId;
    const detailsContainer = document.getElementById(`details-${roleName}`);

    if (detailsContainer.style.display === "block") {
        detailsContainer.style.display = "none";
        return;
    }

    // Hide other open details
    document.querySelectorAll('.role-details').forEach(container => {
        container.style.display = 'none';
    });

    fetch(`/role/${accountId}/${roleName}`)
        .then(response => response.json())
        .then(data => {
            let roleDetailsHTML = '';

            if (data.attached_policies.length > 0) {
                roleDetailsHTML += generatePoliciesHTML('Attached Policies', data.attached_policies, roleName);
            }

            if (data.inline_policies.length > 0) {
                roleDetailsHTML += generatePoliciesHTML('Inline Policies', data.inline_policies, roleName);
            }

            detailsContainer.innerHTML = roleDetailsHTML;
            detailsContainer.style.display = "block";
        })
        .catch(error => {
            console.error('Error fetching role details:', error);
            alert('Failed to fetch role details. Please try again.');
        });
}

// Function to show user details
function showUserDetails(userName, element) {
    const accountId = element.dataset.accountId;
    const detailsContainer = document.getElementById(`details-${userName}`);

    if (detailsContainer.style.display === "block") {
        detailsContainer.style.display = "none";
        return;
    }

    // Hide other open details
    document.querySelectorAll('.user-details').forEach(container => {
        container.style.display = 'none';
    });

    fetch(`/user/${accountId}/${userName}`)
        .then(response => response.json())
        .then(data => {
            let userDetailsHTML = '';

            if (data.attached_policies.length > 0) {
                userDetailsHTML += generatePoliciesHTML('Attached Policies', data.attached_policies, userName);
            }

            if (data.inline_policies.length > 0) {
                userDetailsHTML += generatePoliciesHTML('Inline Policies', data.inline_policies, userName);
            }

            detailsContainer.innerHTML = userDetailsHTML;
            detailsContainer.style.display = "block";
        })
        .catch(error => {
            console.error('Error fetching user details:', error);
            alert('Failed to fetch user details. Please try again.');
        });
}

// Function to toggle policy document visibility
function togglePolicy(policyName, parentName) {
    const policyElement = document.getElementById(`${parentName}-${policyName}`);

    document.querySelectorAll('.policy-document').forEach(element => {
        if (element !== policyElement) {
            element.style.display = "none";
        }
    });

    policyElement.style.display = policyElement.style.display === "none" ? "block" : "none";
}

// Helper function to generate policy HTML
function generatePoliciesHTML(title, policies, parentName) {
    let html = `<div class="card mt-3"><div class="card-body"><h5>${title}:</h5><ul class="list-group mb-3">`;

    policies.forEach(policy => {
        html += `
        <li class="list-group-item">
          <span class="policy-name" style="cursor: pointer" onclick="togglePolicy('${policy.name}', '${parentName}')">
            <i class="fas fa-caret-down"></i> ${policy.name}
          </span>
          <pre id="${parentName}-${policy.name}" class="policy-document hidden p-2 mt-2 bg-white border border-gray-300 rounded-md">${JSON.stringify(policy.document, null, 2)}</pre>
        </li>`;
    });

    html += `</ul></div></div>`;
    return html;
}
