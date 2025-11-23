// Live update for buyer dashboard 'orders waiting for confirmation' counter
function updateBuyerWaitingOrdersCounter(count) {
    const badge = document.getElementById('buyer-waiting-orders-badge');
    const text = document.getElementById('buyer-waiting-orders-count');
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }
    if (text) {
        text.textContent = count;
    }
}

function pollBuyerWaitingOrdersCounter() {
    fetch('/warehouse/dashboard/buyer_order_counts/')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                updateBuyerWaitingOrdersCounter(data.waiting_orders);
            }
        });
    setTimeout(pollBuyerWaitingOrdersCounter, 10000);
}

document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('buyer-waiting-orders-badge')) {
        pollBuyerWaitingOrdersCounter();
    }
});
