// Live update for seller sidebar order counter
function updateSidebarOrderCounter(count) {
    const badge = document.getElementById('sidebar-seller-orders-badge');
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }
}

function pollSidebarOrderCounter() {
    fetch('/warehouse/dashboard/order_counts/')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                updateSidebarOrderCounter(data.new_orders);
            }
        });
    setTimeout(pollSidebarOrderCounter, 10000);
}

document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('sidebar-seller-orders-badge')) {
        pollSidebarOrderCounter();
    }
});
