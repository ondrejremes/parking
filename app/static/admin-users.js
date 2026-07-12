console.log('Setting up Entra ID sync button...');
document.getElementById('syncBtn').addEventListener('click', syncEntraUsers);
console.log('Button listener attached');

async function syncEntraUsers(e) {
    console.log('Button clicked!', e);
    try {
        const btn = document.getElementById('syncBtn');
        const result = document.getElementById('syncResult');
        console.log('Elements found:', { btn, result });

        btn.disabled = true;
        btn.textContent = '⏳ Načítání...';
        console.log('Fetching from /admin/users/entra-sync...');

        const resp = await fetch('/admin/users/entra-sync');
        console.log('Response status:', resp.status, resp.statusText);

        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
        }

        const data = await resp.json();
        console.log('Data received:', data);

        btn.disabled = false;
        btn.textContent = '🔄 Načíst uživatele z Entra ID';

        result.innerHTML = '';

        if (data.new_users.length === 0) {
            console.log('No new users');
            const msg = document.createElement('p');
            const strong = document.createElement('strong');
            strong.textContent = '✅ Všichni uživatelé z Entra ID jsou již zaregistrováni!';
            msg.appendChild(strong);
            msg.appendChild(document.createElement('br'));
            const stats = document.createElement('span');
            stats.textContent = `Registrovaných: ${data.registered_users}, Celkem v Entra ID: ${data.total_entra_users}`;
            msg.appendChild(stats);
            result.appendChild(msg);
            result.classList.add('show');
            return;
        }

        console.log('Found', data.new_users.length, 'new users');

        const title = document.createElement('strong');
        title.textContent = `📋 Nových uživatelů k registraci: ${data.new_users.length}`;
        result.appendChild(title);
        result.appendChild(document.createElement('br'));
        result.appendChild(document.createElement('br'));

        for (const user of data.new_users) {
            const div = document.createElement('div');
            div.className = 'entra-user';

            const name = document.createElement('strong');
            name.textContent = user.displayName;
            div.appendChild(name);
            div.appendChild(document.createElement('br'));

            const email = document.createElement('span');
            email.className = 'entra-email';
            email.textContent = user.mail;
            div.appendChild(email);
            div.appendChild(document.createElement('br'));

            const form = document.createElement('form');
            form.method = 'post';
            form.action = '/admin/users/entra-register';
            form.className = 'entra-form';

            const oid = document.createElement('input');
            oid.type = 'hidden';
            oid.name = 'azure_oid';
            oid.value = user.id;
            form.appendChild(oid);

            const displayName = document.createElement('input');
            displayName.type = 'hidden';
            displayName.name = 'display_name';
            displayName.value = user.displayName;
            form.appendChild(displayName);

            const email_input = document.createElement('input');
            email_input.type = 'hidden';
            email_input.name = 'email';
            email_input.value = user.mail;
            form.appendChild(email_input);

            const csrf = document.createElement('input');
            csrf.type = 'hidden';
            csrf.name = 'csrf_token';
            csrf.value = document.querySelector('input[name="csrf_token"]').value;
            form.appendChild(csrf);

            const btn = document.createElement('button');
            btn.type = 'submit';
            btn.textContent = '+ Zaregistrovat';
            form.appendChild(btn);

            div.appendChild(form);
            result.appendChild(div);
        }

        result.classList.add('show');
        console.log('Display updated');
    } catch (error) {
        console.error('Entra ID sync error:', error);
        const btn = document.getElementById('syncBtn');
        btn.disabled = false;
        btn.textContent = '🔄 Načíst uživatele z Entra ID';
        const result = document.getElementById('syncResult');
        const errorMsg = document.createElement('p');
        errorMsg.className = 'error-message';
        const errorStrong = document.createElement('strong');
        errorStrong.textContent = '⚠️ Chyba: ';
        errorMsg.appendChild(errorStrong);
        const errorText = document.createTextNode(error.message);
        errorMsg.appendChild(errorText);
        result.appendChild(errorMsg);
        result.classList.add('show');
    }
}
