/**
 * Config Builder - Client-side application logic.
 * Config Templates are paired Base + Full configs.
 * Build page: select template, create/load site, fill form, save, download .bin.
 */
(function () {
    'use strict';

    // --- State ---
    let templates = [];
    let siteFiles = [];
    let routerModels = [];
    let currentTemplate = null; // loaded template with base_content, full_content, variables
    let currentSiteRows = [];
    let currentSiteHeaders = [];
    let loadedSiteRowIndex = null; // index of loaded row for editing
    let siteIsSaved = true; // track if form has been saved since last edit

    // Extra fields always present in the form
    const EXTRA_FIELDS = [
        { name: 'RDL', type: 'string' },
        { name: 'Store Name', type: 'string' },
        { name: 'Site Address', type: 'string' },
        { name: 'City', type: 'string' },
        { name: 'EWP ID', type: 'string' },
    ];

    // --- Help Text ---
    const helpTexts = {
        templates: '<strong>Config Templates</strong><br><br>' +
            'A Config Template is a named pair of JSON configs:<br>' +
            '• <strong>Base</strong> — sets up connectivity on install<br>' +
            '• <strong>Full</strong> — applied by a remote admin<br><br>' +
            'Use <code>{{variable_name}}</code> placeholders for per-site values.<br><br>' +
            '<strong>Example:</strong><br>' +
            '<code>{"name": "Vlan2", "ip_address": "{{Vlan2 IP Address}}"}</code><br><br>' +
            '<strong>Supported types:</strong> string, integer, float, boolean, ipv4, ipv6, cidr, mac<br>' +
            'Use <code>{{name|type}}</code> to specify a type, e.g. <code>{{vlan|integer}}</code>',
        build: '<strong>Build Configuration</strong><br><br>' +
            '1. Select a Config Template<br>' +
            '2. Create a new site or load a saved one<br>' +
            '3. Fill in all required fields<br>' +
            '4. Save the site<br>' +
            '5. Download Base and/or Full config as .bin<br><br>' +
            'If you download without saving, you will be prompted to save first.',
        sites: '<strong>Saved Sites</strong><br><br>' +
            'Manage your saved site CSV files. Upload new CSVs or delete existing ones.<br><br>' +
            'Site files are used in the Build tab to load previously saved site data.'
    };

    // --- DOM References ---
    const darkModeToggle = document.getElementById('darkModeToggle');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const navItems = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');
    const notification = document.getElementById('notification');
    const notificationText = document.getElementById('notificationText');
    const helpContent = document.getElementById('helpContent');

    // Templates tab
    const addTemplateBtn = document.getElementById('addTemplateBtn');
    const templateList = document.getElementById('templateList');
    const templateModal = document.getElementById('templateModal');
    const templateModalTitle = document.getElementById('templateModalTitle');
    const closeTemplateModal = document.getElementById('closeTemplateModal');
    const cancelTemplateBtn = document.getElementById('cancelTemplateBtn');
    const saveTemplateBtn = document.getElementById('saveTemplateBtn');
    const templateName = document.getElementById('templateName');
    const baseConfigContent = document.getElementById('baseConfigContent');
    const fullConfigContent = document.getElementById('fullConfigContent');
    const baseConfigFileInput = document.getElementById('baseConfigFileInput');
    const fullConfigFileInput = document.getElementById('fullConfigFileInput');
    const loadBaseFileBtn = document.getElementById('loadBaseFileBtn');
    const loadFullFileBtn = document.getElementById('loadFullFileBtn');
    const baseFileNameLabel = document.getElementById('baseFileNameLabel');
    const fullFileNameLabel = document.getElementById('fullFileNameLabel');
    const templateStepBase = document.getElementById('templateStepBase');
    const templateStepFull = document.getElementById('templateStepFull');
    const nextToFullBtn = document.getElementById('nextToFullBtn');
    const backToBaseBtn = document.getElementById('backToBaseBtn');
    const templateValidation = document.getElementById('templateValidation');

    // Build tab
    const buildTemplateSelect = document.getElementById('buildTemplateSelect');
    const siteModeSection = document.getElementById('siteModeSection');
    const loadSitePanel = document.getElementById('loadSitePanel');
    const loadSiteFileSelect = document.getElementById('loadSiteFileSelect');
    const loadSiteSearchContainer = document.getElementById('loadSiteSearchContainer');
    const loadSiteSearch = document.getElementById('loadSiteSearch');
    const loadSiteResults = document.getElementById('loadSiteResults');
    const siteFormContainer = document.getElementById('siteFormContainer');
    const siteFormFields = document.getElementById('siteFormFields');
    const saveSiteSection = document.getElementById('saveSiteSection');
    const saveSiteFilename = document.getElementById('saveSiteFilename');
    const saveSiteBtn = document.getElementById('saveSiteBtn');
    const downloadSection = document.getElementById('downloadSection');
    const downloadBaseBtn = document.getElementById('downloadBaseBtn');
    const downloadFullBtn = document.getElementById('downloadFullBtn');

    // Sites tab
    const uploadSitesBtn = document.getElementById('uploadSitesBtn');
    const sitesFileInput = document.getElementById('sitesFileInput');
    const siteFilesList = document.getElementById('siteFilesList');


    // ========== TYPE VALIDATION ==========

    function validateValue(value, type) {
        if (value === undefined || value === null || value.trim() === '') return false;
        const v = value.trim();
        switch (type) {
            case 'string': return v.length > 0;
            case 'integer': return /^-?\d+$/.test(v);
            case 'float': return /^-?\d+(\.\d+)?$/.test(v);
            case 'boolean': return v.toLowerCase() === 'true' || v.toLowerCase() === 'false';
            case 'ipv4': {
                const m = v.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
                if (!m) return false;
                return m.slice(1).every(o => parseInt(o, 10) >= 0 && parseInt(o, 10) <= 255);
            }
            case 'ipv6': return /^[0-9A-Fa-f:]+$/.test(v) && v.includes(':');
            case 'cidr': {
                const parts = v.split('/');
                if (parts.length !== 2) return false;
                const prefix = parseInt(parts[1], 10);
                if (isNaN(prefix) || prefix < 0) return false;
                if (parts[0].includes(':')) return /^[0-9A-Fa-f:]+$/.test(parts[0]) && prefix <= 128;
                const cm = parts[0].match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
                if (!cm) return false;
                return cm.slice(1).every(o => parseInt(o, 10) >= 0 && parseInt(o, 10) <= 255) && prefix <= 32;
            }
            case 'mac': return /^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$/.test(v);
            default: return v.length > 0;
        }
    }

    function getTypePlaceholder(type) {
        switch (type) {
            case 'string': return '';
            case 'integer': return 'e.g. 42';
            case 'float': return 'e.g. 3.14';
            case 'boolean': return 'true or false';
            case 'ipv4': return 'e.g. 192.168.1.1';
            case 'ipv6': return 'e.g. 2001:db8::1';
            case 'cidr': return 'e.g. 10.0.0.0/24';
            case 'mac': return 'e.g. AA:BB:CC:DD:EE:FF';
            default: return '';
        }
    }

    // ========== NAVIGATION ==========

    function setActiveTab(tab) {
        navItems.forEach(n => n.classList.remove('active'));
        tabContents.forEach(t => t.classList.remove('active'));
        const activeNav = document.querySelector('.nav-item[data-tab="' + tab + '"]');
        if (activeNav) activeNav.classList.add('active');
        const activeTab = document.getElementById(tab + 'Tab');
        if (activeTab) activeTab.classList.add('active');
        updateHelp(tab);
    }

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            setActiveTab(item.dataset.tab);
        });
    });

    function updateHelp(tab) {
        if (helpContent && helpTexts[tab]) {
            helpContent.innerHTML = helpTexts[tab];
        }
    }

    // --- Dark Mode ---
    function initDarkMode() {
        if (localStorage.getItem('configBuilderDarkMode') === 'true') {
            document.body.classList.add('dark-mode');
        }
    }
    darkModeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        localStorage.setItem('configBuilderDarkMode', document.body.classList.contains('dark-mode'));
    });

    // --- User Guide ---
    const helpGuideBtn = document.getElementById('helpGuideBtn');
    const userGuideModal = document.getElementById('userGuideModal');
    const closeUserGuideModal = document.getElementById('closeUserGuideModal');
    helpGuideBtn.addEventListener('click', () => userGuideModal.classList.add('active'));
    closeUserGuideModal.addEventListener('click', () => userGuideModal.classList.remove('active'));
    userGuideModal.addEventListener('click', (e) => { if (e.target === userGuideModal) userGuideModal.classList.remove('active'); });

    // --- Sidebar ---
    sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('collapsed'));

    // ========== CONFIG TEMPLATES ==========

    async function loadTemplates() {
        try {
            const resp = await fetch('/api/templates');
            const data = await resp.json();
            templates = data.templates || [];
            renderTemplateList();
            populateBuildTemplateSelect();
        } catch (e) {
            templateList.innerHTML = '<div class="loading-message">Error loading templates</div>';
        }
    }

    function renderTemplateList() {
        if (templates.length === 0) {
            templateList.innerHTML = '<div class="empty-state"><h2>No config templates</h2><p>Add a template to get started</p></div>';
            return;
        }
        templateList.innerHTML = templates.map(t => {
            const baseVars = t.base_variables.map(v => '<span class="variable-tag">' + esc(v.name) + '</span>').join('');
            const fullVars = t.full_variables.map(v => '<span class="variable-tag">' + esc(v.name) + '</span>').join('');
            return '<div class="config-item">' +
                '<div class="config-item-content">' +
                '<div class="config-item-name">' + esc(t.name) + '</div>' +
                '<div class="config-item-meta">Base: ' + t.base_variables.length + ' vars | Full: ' + t.full_variables.length + ' vars</div>' +
                '<div class="config-item-vars"><small>Base:</small> ' + (baseVars || '<em>none</em>') + '</div>' +
                '<div class="config-item-vars" style="margin-top:0.25rem;"><small>Full:</small> ' + (fullVars || '<em>none</em>') + '</div>' +
                '</div>' +
                '<div class="config-item-actions">' +
                '<button class="btn btn-sm btn-primary" onclick="app.editTemplate(\'' + escAttr(t.filename) + '\')">Edit</button>' +
                '<button class="btn btn-sm btn-danger" onclick="app.deleteTemplate(\'' + escAttr(t.filename) + '\')">Delete</button>' +
                '</div>' +
                '</div>';
        }).join('');
    }

    // Add Template Modal
    addTemplateBtn.addEventListener('click', () => {
        templateModalTitle.textContent = 'Add Config Template';
        templateName.value = '';
        baseConfigContent.value = '';
        fullConfigContent.value = '';
        baseFileNameLabel.textContent = '';
        fullFileNameLabel.textContent = '';
        templateValidation.style.display = 'none';
        templateStepBase.style.display = 'block';
        templateStepFull.style.display = 'none';
        templateModal.classList.add('active');
    });

    // File upload helper — resets input value to allow re-selecting same file
    async function handleFileUpload(fileInput, textarea, labelEl) {
        const file = fileInput.files[0];
        if (!file) return;
        if (labelEl) labelEl.textContent = file.name;

        if (file.name.toLowerCase().endsWith('.bin')) {
            const reader = new FileReader();
            reader.onload = async (ev) => {
                const bytes = new Uint8Array(ev.target.result);
                let binary = '';
                for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
                const b64 = btoa(binary);
                try {
                    const resp = await fetch('/api/templates/decode-bin', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ bin_base64: b64 })
                    });
                    const data = await resp.json();
                    if (data.error) showNotification('Decode failed: ' + data.error, 'error');
                    else { textarea.value = data.content; showNotification('Decoded .bin to JSON', 'success'); }
                } catch (err) { showNotification('Decode failed', 'error'); }
            };
            reader.readAsArrayBuffer(file);
        } else {
            const reader = new FileReader();
            reader.onload = (ev) => { textarea.value = ev.target.result; };
            reader.readAsText(file);
        }
        // Reset so same file can be selected again
        fileInput.value = '';
    }

    loadBaseFileBtn.addEventListener('click', () => baseConfigFileInput.click());
    loadFullFileBtn.addEventListener('click', () => fullConfigFileInput.click());
    baseConfigFileInput.addEventListener('change', () => handleFileUpload(baseConfigFileInput, baseConfigContent, baseFileNameLabel));
    fullConfigFileInput.addEventListener('change', () => handleFileUpload(fullConfigFileInput, fullConfigContent, fullFileNameLabel));

    // Step navigation
    nextToFullBtn.addEventListener('click', () => {
        const name = templateName.value.trim();
        const base = baseConfigContent.value.trim();
        if (!name) { showNotification('Template name is required', 'error'); return; }
        if (!base) { showNotification('Base config content is required', 'error'); return; }
        templateStepBase.style.display = 'none';
        templateStepFull.style.display = 'block';
    });

    backToBaseBtn.addEventListener('click', () => {
        templateStepFull.style.display = 'none';
        templateStepBase.style.display = 'block';
    });

    saveTemplateBtn.addEventListener('click', async () => {
        const name = templateName.value.trim();
        const base = baseConfigContent.value.trim();
        const full = fullConfigContent.value.trim();
        if (!name) { showNotification('Template name is required', 'error'); return; }
        if (!base) { showNotification('Base config is required', 'error'); return; }
        if (!full) { showNotification('Full config is required', 'error'); return; }

        // Check if name already exists
        const existing = templates.find(t => t.name.toLowerCase() === name.toLowerCase());
        if (existing) {
            if (!confirm('A template named "' + name + '" already exists. Overwrite?')) return;
        }

        try {
            const resp = await fetch('/api/templates/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, base_content: base, full_content: full })
            });
            const data = await resp.json();
            if (data.error) {
                templateValidation.style.display = 'block';
                templateValidation.className = 'output-status error';
                templateValidation.textContent = data.error;
            } else {
                templateModal.classList.remove('active');
                showNotification('Template saved: ' + data.name, 'success');
                loadTemplates();
            }
        } catch (e) { showNotification('Save failed: ' + e.message, 'error'); }
    });

    closeTemplateModal.addEventListener('click', () => templateModal.classList.remove('active'));
    cancelTemplateBtn.addEventListener('click', () => templateModal.classList.remove('active'));
    templateModal.addEventListener('click', (e) => { if (e.target === templateModal) templateModal.classList.remove('active'); });

    window.app = window.app || {};
    window.app.deleteTemplate = async function (filename) {
        if (!confirm('Delete this template? This cannot be undone.')) return;
        try {
            const resp = await fetch('/api/templates/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename })
            });
            const data = await resp.json();
            if (data.error) showNotification(data.error, 'error');
            else { showNotification('Template deleted', 'success'); loadTemplates(); }
        } catch (e) { showNotification('Delete failed', 'error'); }
    };

    window.app.editTemplate = async function (filename) {
        try {
            const resp = await fetch('/api/templates/load', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename })
            });
            const data = await resp.json();
            if (data.error) { showNotification(data.error, 'error'); return; }
            templateModalTitle.textContent = 'Edit Config Template';
            templateName.value = data.name;
            baseConfigContent.value = data.base_content;
            fullConfigContent.value = data.full_content;
            baseFileNameLabel.textContent = '';
            fullFileNameLabel.textContent = '';
            templateValidation.style.display = 'none';
            templateStepBase.style.display = 'block';
            templateStepFull.style.display = 'none';
            templateModal.classList.add('active');
        } catch (e) { showNotification('Failed to load template', 'error'); }
    };

    // ========== BUILD TAB ==========

    function populateBuildTemplateSelect() {
        buildTemplateSelect.innerHTML = '<option value="">-- Select a Config Template --</option>' +
            templates.map(t => '<option value="' + escAttr(t.filename) + '">' + esc(t.name) + '</option>').join('');

        // Auto-select if only one template
        if (templates.length === 1) {
            buildTemplateSelect.value = templates[0].filename;
            buildTemplateSelect.dispatchEvent(new Event('change'));
        }
    }

    buildTemplateSelect.addEventListener('change', async () => {
        const filename = buildTemplateSelect.value;
        if (!filename) {
            currentTemplate = null;
            siteModeSection.style.display = 'none';
            siteFormContainer.style.display = 'none';
            saveSiteSection.style.display = 'none';
            downloadSection.style.display = 'none';
            return;
        }
        try {
            const resp = await fetch('/api/templates/load', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename })
            });
            const data = await resp.json();
            if (data.error) { showNotification(data.error, 'error'); return; }
            currentTemplate = data;
            siteModeSection.style.display = 'block';
            handleSiteModeChange();
        } catch (e) { showNotification('Failed to load template', 'error'); }
    });

    // Site mode radio
    document.querySelectorAll('input[name="siteMode"]').forEach(radio => {
        radio.addEventListener('change', handleSiteModeChange);
    });

    function getSiteMode() {
        const checked = document.querySelector('input[name="siteMode"]:checked');
        return checked ? checked.value : 'create';
    }

    function handleSiteModeChange() {
        const mode = getSiteMode();
        if (mode === 'create') {
            loadSitePanel.style.display = 'none';
            loadedSiteRowIndex = null;
            buildSiteForm();
            siteFormContainer.style.display = 'block';
            saveSiteSection.style.display = 'block';
            downloadSection.style.display = 'block';
        } else {
            loadSitePanel.style.display = 'block';
            siteFormContainer.style.display = 'none';
            saveSiteSection.style.display = 'none';
            downloadSection.style.display = 'none';
            populateLoadSiteFileSelect();
        }
    }

    function getMergedVariables() {
        if (!currentTemplate) return [];
        const seen = new Set();
        const vars = [];
        // Add extra fields first
        EXTRA_FIELDS.forEach(f => {
            seen.add(f.name);
            vars.push(f);
        });
        // Add Router Model as special (handled separately in form)
        // Add template variables (deduplicated)
        const allTemplateVars = [...(currentTemplate.base_variables || []), ...(currentTemplate.full_variables || [])];
        allTemplateVars.forEach(v => {
            if (!seen.has(v.name)) {
                seen.add(v.name);
                vars.push(v);
            }
        });
        return vars;
    }

    function buildSiteForm(prefillData) {
        const vars = getMergedVariables();
        let html = '';

        // Router Model selector
        html += '<div class="form-group">' +
            '<label for="field_Router_Model">Router Model</label>' +
            '<select id="field_Router_Model" class="input-field" data-fieldname="Router Model">';
        routerModels.forEach(m => {
            const selected = (prefillData && prefillData['Router Model'] === m) ? ' selected' : (m === 'E3000' && !prefillData ? ' selected' : '');
            html += '<option value="' + esc(m) + '"' + selected + '>' + esc(m) + '</option>';
        });
        html += '</select></div>';

        // Other fields
        vars.forEach(v => {
            const fieldId = 'field_' + v.name.replace(/[^a-zA-Z0-9]/g, '_');
            const prefillVal = prefillData ? (prefillData[v.name] || '') : '';
            const typeLabel = v.type !== 'string' ? ' <small>(' + esc(v.type) + ')</small>' : '';
            const isTemplateVar = !EXTRA_FIELDS.some(ef => ef.name === v.name);
            const extraClass = isTemplateVar ? ' template-var-field' : '';
            html += '<div class="form-group' + extraClass + '">' +
                '<label for="' + fieldId + '">' + esc(v.name) + typeLabel + '</label>' +
                '<input type="text" id="' + fieldId + '" class="input-field site-field" data-fieldname="' + escAttr(v.name) + '" data-fieldtype="' + esc(v.type) + '" placeholder="' + getTypePlaceholder(v.type) + '" value="' + escAttr(prefillVal) + '">' +
                '<span class="field-error" id="err_' + fieldId + '"></span>' +
                '</div>';
        });

        siteFormFields.innerHTML = html;
        siteFormContainer.style.display = 'block';
        saveSiteSection.style.display = 'block';
        downloadSection.style.display = 'block';
        siteIsSaved = !!prefillData; // if prefilled from load, consider saved

        // Track changes and update button states
        updateActionButtons();
        siteFormFields.querySelectorAll('input, select').forEach(el => {
            el.addEventListener('input', () => { siteIsSaved = false; updateActionButtons(); });
            el.addEventListener('change', () => { siteIsSaved = false; updateActionButtons(); });
        });
    }

    function isFormComplete() {
        let complete = true;
        siteFormFields.querySelectorAll('.site-field').forEach(input => {
            if (!input.value.trim()) complete = false;
        });
        return complete;
    }

    function updateActionButtons() {
        const complete = isFormComplete();
        saveSiteBtn.disabled = !complete;
        downloadBaseBtn.disabled = !complete;
        downloadFullBtn.disabled = !complete;
        const tooltip = complete ? '' : 'Complete all fields to enable';
        saveSiteBtn.title = tooltip;
        downloadBaseBtn.title = tooltip;
        downloadFullBtn.title = tooltip;
    }

    function getFormData() {
        const data = {};
        // Router Model
        const rmSelect = document.getElementById('field_Router_Model');
        if (rmSelect) data['Router Model'] = rmSelect.value;
        // All other fields
        siteFormFields.querySelectorAll('.site-field').forEach(input => {
            data[input.dataset.fieldname] = input.value.trim();
        });
        return data;
    }

    function validateForm() {
        let valid = true;
        siteFormFields.querySelectorAll('.site-field').forEach(input => {
            const name = input.dataset.fieldname;
            const type = input.dataset.fieldtype;
            const val = input.value.trim();
            const errEl = document.getElementById('err_field_' + name.replace(/[^a-zA-Z0-9]/g, '_'));
            if (!val) {
                if (errEl) { errEl.textContent = 'Required'; errEl.style.display = 'block'; }
                valid = false;
            } else if (!validateValue(val, type)) {
                if (errEl) { errEl.textContent = 'Invalid ' + type; errEl.style.display = 'block'; }
                valid = false;
            } else {
                if (errEl) { errEl.textContent = ''; errEl.style.display = 'none'; }
            }
        });
        return valid;
    }

    // --- Save Site ---
    saveSiteBtn.addEventListener('click', async () => {
        if (!validateForm()) { showNotification('Please fix form errors', 'error'); return; }
        const filename = saveSiteFilename.value.trim() || 'sites.csv';
        const row = getFormData();

        try {
            const resp = await fetch('/api/sites/save-row', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename, row, row_index: loadedSiteRowIndex })
            });
            const data = await resp.json();
            if (data.error) { showNotification(data.error, 'error'); return; }
            siteIsSaved = true;
            showNotification('Site saved to ' + data.filename, 'success');
            loadSiteFiles();
        } catch (e) { showNotification('Save failed: ' + e.message, 'error'); }
    });

    // --- Download Configs ---
    async function downloadConfig(type) {
        if (!validateForm()) { showNotification('Please fix form errors before downloading', 'error'); return; }

        // Prompt to save if not saved
        if (!siteIsSaved) {
            const shouldSave = confirm('Site has not been saved. Save before downloading?');
            if (shouldSave) {
                const filename = saveSiteFilename.value.trim() || 'sites.csv';
                const row = getFormData();
                try {
                    const resp = await fetch('/api/sites/save-row', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filename, row, row_index: loadedSiteRowIndex })
                    });
                    const data = await resp.json();
                    if (data.error) { showNotification(data.error, 'error'); return; }
                    siteIsSaved = true;
                    showNotification('Site saved to ' + data.filename, 'success');
                    loadSiteFiles();
                } catch (e) { showNotification('Save failed: ' + e.message, 'error'); return; }
            }
        }

        // Build the config
        const formData = getFormData();
        const content = type === 'base' ? currentTemplate.base_content : currentTemplate.full_content;
        const variables = type === 'base' ? currentTemplate.base_variables : currentTemplate.full_variables;

        let result = content;
        for (const v of variables) {
            const val = formData[v.name] || '';
            const regex = new RegExp('\\{\\{\\s*' + escapeRegex(v.name) + '(\\s*\\|\\s*\\w+)?\\s*\\}\\}', 'g');
            result = result.replace(regex, val);
        }

        // Encode as .bin
        try {
            const resp = await fetch('/api/build/encode-bin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: result })
            });
            const data = await resp.json();
            if (data.error) { showNotification(data.error, 'error'); return; }

            const rdl = formData['RDL'] || 'unknown';
            const model = formData['Router Model'] || 'E3000';
            const label = type === 'base' ? 'Base' : 'Full';
            const binFilename = 'RDL' + rdl + ' - ' + model + ' - ' + label + ' Config.bin';

            const binaryStr = atob(data.bin_base64);
            const bytes = new Uint8Array(binaryStr.length);
            for (let i = 0; i < binaryStr.length; i++) bytes[i] = binaryStr.charCodeAt(i);
            const blob = new Blob([bytes], { type: 'application/octet-stream' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = binFilename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showNotification('Downloaded ' + binFilename, 'success');
        } catch (e) { showNotification('Download failed: ' + e.message, 'error'); }
    }

    downloadBaseBtn.addEventListener('click', () => downloadConfig('base'));
    downloadFullBtn.addEventListener('click', () => downloadConfig('full'));

    // ========== LOAD SAVED SITE ==========

    function populateLoadSiteFileSelect() {
        loadSiteFileSelect.innerHTML = '<option value="">-- Select a site file --</option>' +
            siteFiles.map(f => '<option value="' + escAttr(f.name) + '">' + esc(f.name) + ' (' + f.row_count + ' sites)</option>').join('');

        // If only one file, auto-select it
        if (siteFiles.length === 1) {
            loadSiteFileSelect.value = siteFiles[0].name;
            loadSiteFile(siteFiles[0].name);
        }
    }

    loadSiteFileSelect.addEventListener('change', () => {
        const name = loadSiteFileSelect.value;
        if (!name) {
            loadSiteSearchContainer.style.display = 'none';
            siteFormContainer.style.display = 'none';
            saveSiteSection.style.display = 'none';
            downloadSection.style.display = 'none';
            return;
        }
        loadSiteFile(name);
    });

    async function loadSiteFile(name) {
        try {
            const resp = await fetch('/api/sites/load', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            const data = await resp.json();
            if (data.error) { showNotification(data.error, 'error'); return; }
            currentSiteRows = data.rows;
            currentSiteHeaders = data.headers;
            loadSiteSearchContainer.style.display = 'block';
            loadSiteSearch.value = '';
            renderLoadSiteResults('');
        } catch (e) { showNotification('Failed to load sites', 'error'); }
    }

    loadSiteSearch.addEventListener('input', () => {
        renderLoadSiteResults(loadSiteSearch.value);
    });

    function renderLoadSiteResults(query) {
        const q = query.toLowerCase().trim();
        const filtered = q
            ? currentSiteRows.filter(row => Object.values(row).some(v => String(v).toLowerCase().includes(q)))
            : currentSiteRows;

        if (filtered.length === 0) {
            loadSiteResults.innerHTML = '<div class="loading-message">No matching sites</div>';
            return;
        }

        const maxShow = 50;
        const shown = filtered.slice(0, maxShow);
        loadSiteResults.innerHTML = shown.map(row => {
            const realIdx = currentSiteRows.indexOf(row);
            const preview = Object.entries(row).slice(0, 4).map(([k, v]) => esc(k) + ': ' + esc(v)).join(' | ');
            return '<div class="location-result-item" data-idx="' + realIdx + '">' +
                '<span class="location-result-text">' + preview + '</span></div>';
        }).join('') + (filtered.length > maxShow ? '<div class="loading-message">' + (filtered.length - maxShow) + ' more...</div>' : '');

        loadSiteResults.querySelectorAll('.location-result-item').forEach(item => {
            item.addEventListener('click', () => {
                const idx = parseInt(item.dataset.idx);
                selectLoadedSite(idx);
            });
        });
    }

    function selectLoadedSite(idx) {
        const row = currentSiteRows[idx];
        loadedSiteRowIndex = idx;
        saveSiteFilename.value = loadSiteFileSelect.value || 'sites.csv';
        buildSiteForm(row);
    }

    // ========== SAVED SITES TAB ==========

    async function loadSiteFiles() {
        try {
            const resp = await fetch('/api/sites');
            const data = await resp.json();
            siteFiles = data.files || [];
            renderSiteFilesList();
        } catch (e) {
            siteFilesList.innerHTML = '<div class="loading-message">Error loading sites</div>';
        }
    }

    function renderSiteFilesList() {
        if (siteFiles.length === 0) {
            siteFilesList.innerHTML = '<div class="empty-state"><h2>No site files</h2><p>Upload a CSV or save sites from the Build tab</p></div>';
            return;
        }
        siteFilesList.innerHTML = siteFiles.map(f => {
            return '<div class="config-item">' +
                '<div class="config-item-content">' +
                '<div class="config-item-name">' + esc(f.name) + '</div>' +
                '<div class="config-item-meta">' + f.row_count + ' site(s) &middot; ' + f.headers.length + ' columns</div>' +
                '</div>' +
                '<div class="config-item-actions">' +
                '<button class="btn btn-sm btn-danger" onclick="app.deleteSiteFile(\'' + escAttr(f.name) + '\')">Delete</button>' +
                '</div>' +
                '</div>';
        }).join('');
    }

    uploadSitesBtn.addEventListener('click', () => sitesFileInput.click());
    sitesFileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = async (ev) => {
            try {
                const resp = await fetch('/api/sites/upload', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: file.name, content: ev.target.result })
                });
                const data = await resp.json();
                if (data.error) showNotification(data.error, 'error');
                else { showNotification('Uploaded ' + data.name + ' (' + data.row_count + ' sites)', 'success'); loadSiteFiles(); }
            } catch (err) { showNotification('Upload failed', 'error'); }
        };
        reader.readAsText(file);
        sitesFileInput.value = '';
    });

    window.app.deleteSiteFile = async function (name) {
        if (!confirm('Delete "' + name + '"?')) return;
        try {
            const resp = await fetch('/api/sites/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            const data = await resp.json();
            if (data.error) showNotification(data.error, 'error');
            else { showNotification('Deleted ' + name, 'success'); loadSiteFiles(); }
        } catch (e) { showNotification('Delete failed', 'error'); }
    };

    // ========== ROUTER MODELS ==========

    async function loadRouterModels() {
        try {
            const resp = await fetch('/api/router-models');
            const data = await resp.json();
            routerModels = data.models || ['E3000'];
        } catch (e) {
            routerModels = ['E3000'];
        }
    }

    // ========== UTILITIES ==========

    function esc(str) {
        const div = document.createElement('div');
        div.textContent = String(str);
        return div.innerHTML;
    }

    function escAttr(str) {
        return String(str).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
    }

    function escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function showNotification(message, type) {
        notificationText.textContent = message;
        notification.className = 'notification show ' + type;
        setTimeout(() => notification.classList.remove('show'), 3000);
    }

    // ========== INIT ==========

    initDarkMode();
    updateHelp('templates');

    // Load data
    (async function init() {
        await loadRouterModels();
        await loadTemplates();
        await loadSiteFiles();
    })();

})();
