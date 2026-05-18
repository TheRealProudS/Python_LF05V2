// Confirmation helpers
(function(){
    document.addEventListener('click', function(e){
        const el = e.target.closest('[data-confirm]');
        if(!el) return;
        const msg = el.getAttribute('data-confirm') || 'Sind Sie sicher?';
        if(!confirm(msg)){
            e.preventDefault();
        }
    });

    window.confirmTransfer = function(form){
        try{
            const amountEl = form.querySelector('[name="betrag"]');
            const targetEl = form.querySelector('[name="ziel_kontonummer"]');
            const amount = amountEl ? parseFloat(amountEl.value) : NaN;
            const target = targetEl ? targetEl.value : '';
            if(isNaN(amount) || amount <= 0){
                alert('Bitte gültigen Betrag eingeben.');
                return false;
            }
            const txt = `Überweisung an ${target} über ${amount.toFixed(2)} € bestätigen?`;
            return confirm(txt);
        }catch(err){
            return confirm('Überweisung bestätigen?');
        }
    }
})();
