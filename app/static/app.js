document.addEventListener('DOMContentLoaded', function () {

    // [data-open-dialog="dlg-id"] → opens the <dialog>
    document.querySelectorAll('[data-open-dialog]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var dlg = document.getElementById(this.dataset.openDialog);
            if (dlg) dlg.showModal();
        });
    });

    // [data-close-dialog="dlg-id"] → closes the <dialog>
    document.querySelectorAll('[data-close-dialog]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var dlg = document.getElementById(this.dataset.closeDialog);
            if (dlg) dlg.close();
        });
    });

    // Radio in reservation dialog: [data-pick-date="YYYY-MM-DD"]
    // Updates hidden #sid-DATE and #shf-DATE when selection changes
    document.querySelectorAll('input[data-pick-date]').forEach(function (radio) {
        radio.addEventListener('change', function () {
            var dk = this.dataset.pickDate;
            var parts = this.value.split('|');
            var sid = document.getElementById('sid-' + dk);
            var shf = document.getElementById('shf-' + dk);
            if (sid) sid.value = parts[0];
            if (shf) shf.value = parts[1];
        });
    });

    // Forms with [data-confirm="message"] → show native confirm before submit
    document.querySelectorAll('form[data-confirm]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!confirm(this.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

});
