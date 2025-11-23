(function(){
  // Gate background polling scripts in warehouse/base.html when user is not authenticated
  var isAuthenticated = (window.isAuthenticated === true) || (typeof window.userIsSeller !== 'undefined' && window.userIsSeller === true);
  if (!isAuthenticated) {
    // Disable buyer/seller sidebar counters if they try to run
    if (window.sidebarBuyerCartCounter && typeof window.sidebarBuyerCartCounter.stop === 'function') {
      try { window.sidebarBuyerCartCounter.stop(); } catch(e) {}
    }
    if (window.sidebarOrderCounter && typeof window.sidebarOrderCounter.stop === 'function') {
      try { window.sidebarOrderCounter.stop(); } catch(e) {}
    }
  }
})();
