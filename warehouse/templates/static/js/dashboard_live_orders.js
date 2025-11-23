// Live update for seller dashboard order counters
function updateSellerOrderCounters(newOrders, totalSales) {
    const newOrdersElem = document.getElementById('seller-new-orders-count');
    const totalSalesElem = document.getElementById('seller-total-sales-count');
    if (newOrdersElem) newOrdersElem.textContent = newOrders;
    if (totalSalesElem) totalSalesElem.textContent = totalSales;
}

// Poll the backend every 10 seconds for new order counts
function pollSellerOrderCounts() {
    fetch('/warehouse/dashboard/order_counts/')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                updateSellerOrderCounters(data.new_orders, data.total_sales);
            }
        });
    setTimeout(pollSellerOrderCounts, 10000);
}

document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('seller-new-orders-count')) {
        pollSellerOrderCounts();
    }
});
