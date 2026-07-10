const modal = document.getElementById('editModal');

document.addEventListener('click', (e) => {
    const btn = e.target.closest('.edit-btn');
    if (!btn) return;

    const spotId = btn.dataset.spotId;
    const floor = btn.dataset.floor;
    const number = btn.dataset.number;
    const spotType = btn.dataset.type;
    const assignedUserId = btn.dataset.assigned;
    const active = btn.dataset.active === '1';

    document.getElementById('editFloor').value = floor;
    document.getElementById('editNumber').value = number;
    document.getElementById('editType').value = spotType;
    document.getElementById('editAssigned').value = assignedUserId;
    document.getElementById('editActive').checked = active;

    const form = document.getElementById('editForm');
    form.action = `/admin/spots/${spotId}/edit`;

    modal.style.display = 'flex';
});

document.addEventListener('click', (e) => {
    if (e.target.closest('.close-btn')) {
        modal.style.display = 'none';
    }
    if (e.target === modal) {
        modal.style.display = 'none';
    }
});
