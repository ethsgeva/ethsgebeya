// Live update for buyer sidebar cart counter
function updateSidebarBuyerCartCounter(count) {
    const badge = document.getElementById('sidebar-buyer-cart-badge');
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }
}

function pollSidebarBuyerCartCounter() {
    fetch('/warehouse/dashboard/buyer_cart_count/')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                updateSidebarBuyerCartCounter(data.cart_count);
            }
        });
    setTimeout(pollSidebarBuyerCartCounter, 10000);
}

document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('sidebar-buyer-cart-badge')) {
        pollSidebarBuyerCartCounter();
    }
});
