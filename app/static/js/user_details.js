function togglePolicy(policyId) {
    const policyElement = document.getElementById(policyId);

    document.querySelectorAll('.policy-document').forEach(element => {
        if (element !== policyElement) {
            element.style.display = "none";
        }
    });

    policyElement.style.display = policyElement.style.display === "none" ? "block" : "none";
}

function filterAccounts() {
    const input = document.getElementById('accountSearchInput');
    const filter = input.value.toLowerCase();
    const accountCards = document.querySelectorAll('.account-card');

    accountCards.forEach(card => {
        const accountName = card.getAttribute('data-account-name').toLowerCase();
        card.style.display = accountName.includes(filter) ? '' : 'none';
    });
}
