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

// Sidebar toggle (persist state in localStorage)
(function(){
    document.addEventListener('DOMContentLoaded', function(){
        const shell = document.querySelector('.app-shell');
        const btn = document.getElementById('sidebarToggle');
        const storageKey = 'sidebarCollapsed';
        const setCollapsed = function(collapsed){
            if(!shell) return;
            if(collapsed) shell.classList.add('collapsed'); else shell.classList.remove('collapsed');
            if(btn){
                const icon = btn.querySelector('i');
                if(icon) icon.className = collapsed ? 'bi bi-chevron-right' : 'bi bi-chevron-left';
                btn.setAttribute('aria-expanded', String(!collapsed));
            }
            try{ localStorage.setItem(storageKey, collapsed ? '1' : '0'); }catch(e){}
        };

        if(btn && shell){
            btn.addEventListener('click', function(e){
                const to = !shell.classList.contains('collapsed');
                setCollapsed(to);
            });
            const stored = (localStorage.getItem(storageKey) === '1');
            setCollapsed(stored);
        }

        // Filter panel toggle
        const filterBtn = document.getElementById('filterToggle');
        const filterPanel = document.getElementById('filterPanel');
        if(filterBtn && filterPanel){
            const updateLabel = () => {
                const isCollapsed = filterPanel.classList.contains('collapsed');
                filterBtn.setAttribute('aria-expanded', String(!isCollapsed));
                filterBtn.textContent = isCollapsed ? 'Filter anzeigen' : 'Filter verbergen';
            };
            filterBtn.addEventListener('click', function(e){
                e.preventDefault();
                filterPanel.classList.toggle('collapsed');
                filterPanel.classList.toggle('expanded');
                updateLabel();
            });
            // initialize label based on current panel state
            updateLabel();
        }
    });
})();
