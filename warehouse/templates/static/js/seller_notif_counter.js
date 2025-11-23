// seller_notif_counter.js
// Fetches the seller's pending order count every 10 seconds and updates the notification badge
function updateSellerNotifCounter() {
    fetch('/warehouse/api/seller/order-notifications/', { credentials: 'same-origin' })
        .then(response => response.json())
        .then(data => {
            const notifCounter = document.getElementById('notif-counter');
            if (notifCounter) {
                if (data.count > 0) {
                    notifCounter.textContent = data.count;
                    notifCounter.style.display = 'inline-block';
                } else {
                    notifCounter.textContent = '';
                    notifCounter.style.display = 'none';
                }
            }
        });
}

if (window.userIsSeller) {
    updateSellerNotifCounter();
    setInterval(updateSellerNotifCounter, 10000);
}
