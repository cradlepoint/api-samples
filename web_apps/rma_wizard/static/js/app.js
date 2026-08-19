/**
 * RMA Configuration Migration Wizard
 * Main application JavaScript
 */

// Application state
const AppState = {
    apiKeys: null,
    groups: [],
    sourceRouter: null,
    sourceGroupId: null,
    sourceConfig: null,
    destRouter: null,
    destGroupId: null,
    maskedFields: [],          // Array of {path, resolution, customValue}
    removedFields: [],         // Paths of fields removed from config (need manual update)
    resolvedConfig: null,      // Device config with masked fields resolved
    stepsCompleted: 0
};

// Initialize on DOM ready
$(document).ready(function() {
    initNavigation();
    initDarkMode();
    initPasswordToggles();
    initEventListeners();
    loadAppVersion();
});

function loadAppVersion() {
    $.get('/api/version', function(response) {
        if (response.version) {
            $('#app-version').text('v' + response.version);
        }
    });
}

// ============================================================
// Navigation
// ============================================================

function initNavigation() {
    $('.nav-item').click(function(e) {
        e.preventDefault();
        if ($(this).hasClass('disabled')) return;
        const section = $(this).data('section');
        showSection(section);
    });
}

function showSection(sectionId) {
    $('.element-section').removeClass('active');
    $('#' + sectionId).addClass('active');
    $('.nav-item').removeClass('active');
    $(`.nav-item[data-section="${sectionId}"]`).addClass('active');
}

function enableNavStep(sectionId) {
    $(`.nav-item[data-section="${sectionId}"]`).removeClass('disabled');
}

function setNavStatus(stepName, success) {
    const statusEl = $(`#nav-status-${stepName}`);
    if (success) {
        statusEl.html('<i class="fas fa-check-circle"></i>');
    } else {
        statusEl.html('<i class="fas fa-times-circle"></i>');
    }
}

function updateProgress(step) {
    AppState.stepsCompleted = step;
    const total = 7;
    const pct = Math.round((step / total) * 100);
    $('#progress-fill').css('width', pct + '%');
    $('#progress-text').text(`Step ${step} of ${total}`);
}

// ============================================================
// Dark Mode
// ============================================================

function initDarkMode() {
    const saved = localStorage.getItem('rma-wizard-theme');
    if (saved === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        $('#dark-mode-toggle i').removeClass('fa-moon').addClass('fa-sun');
    }

    $('#dark-mode-toggle').click(function() {
        const current = document.documentElement.getAttribute('data-theme');
        if (current === 'dark') {
            document.documentElement.removeAttribute('data-theme');
            localStorage.setItem('rma-wizard-theme', 'light');
            $(this).find('i').removeClass('fa-sun').addClass('fa-moon');
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('rma-wizard-theme', 'dark');
            $(this).find('i').removeClass('fa-moon').addClass('fa-sun');
        }
    });

    // Help button
    $('#help-toggle').click(function() {
        $('#help-modal').fadeIn(200);
    });
}

// ============================================================
// Password Toggle
// ============================================================

function initPasswordToggles() {
    $('.password-toggle').click(function() {
        const targetId = $(this).data('target');
        const input = $('#' + targetId);
        const icon = $(this).find('i');

        if (input.attr('type') === 'password') {
            input.attr('type', 'text');
            icon.removeClass('fa-eye').addClass('fa-eye-slash');
        } else {
            input.attr('type', 'password');
            icon.removeClass('fa-eye-slash').addClass('fa-eye');
        }
    });
}

// ============================================================
// Event Listeners
// ============================================================

function initEventListeners() {
    // API Keys validation
    $('#validate-api-keys-btn').click(validateApiKeys);

    // Source group selection
    $('#source-group-select').change(function() {
        const groupId = $(this).val();
        if (groupId) {
            loadRoutersForGroup(groupId, 'source');
        } else {
            resetRouterSelect('source');
        }
    });

    // Source router selection
    $('#source-router-select').change(function() {
        const routerId = $(this).val();
        if (routerId) {
            loadRouterDetails(routerId, 'source');
        } else {
            $('#source-router-details').hide();
        }
    });

    // Confirm source device
    $('#confirm-source-btn').click(confirmSourceDevice);

    // Config confirmed
    $('#confirm-config-btn').click(function() {
        updateProgress(3);
        setNavStatus('config', true);
        enableNavStep('dest-device-section');
        showSection('dest-device-section');
        populateDestGroupDropdown();
    });

    // Destination group selection
    $('#dest-group-select').change(function() {
        const groupId = $(this).val();
        if (groupId) {
            loadRoutersForGroup(groupId, 'dest');
        } else {
            resetRouterSelect('dest');
        }
    });

    // Destination router selection
    $('#dest-router-select').change(function() {
        const routerId = $(this).val();
        if (routerId) {
            loadRouterDetails(routerId, 'dest');
        } else {
            $('#dest-router-details').hide();
        }
    });

    // Validate destination
    $('#validate-dest-btn').click(validateDestination);

    // Confirm destination config (masked field resolution)
    $('#confirm-dest-config-btn').click(confirmDestConfig);

    // Apply migration
    $('#apply-migration-btn').click(applyMigration);

    // Re-verify
    $('#reverify-btn').click(verifyMigration);
}

// ============================================================
// API Key Validation
// ============================================================

function validateApiKeys() {
    const apiKeys = {
        'X-CP-API-ID': $('#x-cp-api-id').val().trim(),
        'X-CP-API-KEY': $('#x-cp-api-key').val().trim(),
        'X-ECM-API-ID': $('#x-ecm-api-id').val().trim(),
        'X-ECM-API-KEY': $('#x-ecm-api-key').val().trim()
    };

    const missing = Object.entries(apiKeys)
        .filter(([k, v]) => !v)
        .map(([k]) => k);

    if (missing.length > 0) {
        showValidationStatus('api-key-validation-status', 'error',
            `Please fill in all required fields: ${missing.join(', ')}`);
        return;
    }

    showLoading('Validating API keys...');

    $.ajax({
        url: '/api/validate-api-keys',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ api_keys: apiKeys }),
        success: function(response) {
            hideLoading();
            if (response.success) {
                AppState.apiKeys = apiKeys;
                setNavStatus('api-keys', true);
                updateProgress(1);
                enableNavStep('source-device-section');
                showToast('success', 'API keys validated successfully');

                // Auto-collapse info boxes now that validation passed
                collapseDefaultInfoBoxes('#api-keys-section');

                setTimeout(function() {
                    showSection('source-device-section');
                    loadGroups();
                }, 800);
            } else {
                showValidationStatus('api-key-validation-status', 'error', response.message);
                setNavStatus('api-keys', false);
                showToast('error', 'API key validation failed');
            }
        },
        error: function(xhr) {
            hideLoading();
            const msg = xhr.responseJSON ? xhr.responseJSON.message : 'Network error';
            showValidationStatus('api-key-validation-status', 'error', msg);
            showToast('error', 'Connection error during validation');
        }
    });
}

// ============================================================
// Groups
// ============================================================

function loadGroups() {
    $.ajax({
        url: '/api/get-groups',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ api_keys: AppState.apiKeys }),
        success: function(response) {
            if (response.success) {
                AppState.groups = response.groups;
                populateGroupDropdown('source-group-select', response.groups);
            } else {
                showToast('error', 'Failed to load groups: ' + response.message);
            }
        },
        error: function() {
            showToast('error', 'Network error loading groups');
        }
    });
}

function populateGroupDropdown(selectId, groups) {
    const select = $('#' + selectId);
    select.empty().append('<option value="">-- Select a group --</option>');

    groups.forEach(function(group) {
        const label = group.product_name
            ? `${group.name} (${group.product_name})`
            : group.name;
        select.append(`<option value="${group.id}">${escapeHtml(label)}</option>`);
    });
}

function populateDestGroupDropdown() {
    if (AppState.groups.length > 0) {
        populateGroupDropdown('dest-group-select', AppState.groups);
    } else {
        $.ajax({
            url: '/api/get-groups',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ api_keys: AppState.apiKeys }),
            success: function(response) {
                if (response.success) {
                    AppState.groups = response.groups;
                    populateGroupDropdown('dest-group-select', response.groups);
                }
            }
        });
    }
}

// ============================================================
// Router Dropdown
// ============================================================

function loadRoutersForGroup(groupId, context) {
    const loadingEl = $(`#${context}-group-loading`);
    const routerSelect = $(`#${context}-router-select`);

    loadingEl.show();
    routerSelect.prop('disabled', true).empty().append('<option value="">Loading routers...</option>');
    $(`#${context}-router-details`).hide();

    if (context === 'source') {
        AppState.sourceGroupId = groupId;
    } else {
        AppState.destGroupId = groupId;
    }

    $.ajax({
        url: '/api/get-routers',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            api_keys: AppState.apiKeys,
            group_id: groupId
        }),
        success: function(response) {
            loadingEl.hide();
            if (response.success) {
                populateRouterDropdown(routerSelect, response.routers);
            } else {
                routerSelect.empty().append('<option value="">Error loading routers</option>');
                showToast('error', response.message);
            }
        },
        error: function() {
            loadingEl.hide();
            routerSelect.empty().append('<option value="">Network error</option>');
            showToast('error', 'Network error loading routers');
        }
    });
}

function populateRouterDropdown(selectEl, routers) {
    selectEl.empty().append('<option value="">-- Select a router --</option>');

    if (!routers || routers.length === 0) {
        selectEl.append('<option value="" disabled>No routers in this group</option>');
        selectEl.prop('disabled', true);
        return;
    }

    routers.forEach(function(router) {
        const stateIndicator = router.state === 'online' ? '\u25CF' :  // filled circle
                               router.state === 'offline' ? '\u25CB' : // empty circle
                               '\u25CB';
        const stateLabel = router.state === 'online' ? ' [online]' :
                           router.state === 'offline' ? ' [offline]' : '';
        const label = `${stateIndicator} ${router.name || 'Unnamed'} (ID: ${router.id})${stateLabel}`;
        const opt = $(`<option value="${router.id}">${escapeHtml(label)}</option>`);
        // Store state as data attribute for CSS coloring
        opt.attr('data-state', router.state || 'unknown');
        selectEl.append(opt);
    });

    selectEl.prop('disabled', false);
}

function resetRouterSelect(context) {
    const routerSelect = $(`#${context}-router-select`);
    routerSelect.prop('disabled', true).empty().append('<option value="">-- Select a group first --</option>');
    $(`#${context}-router-details`).hide();
}

// ============================================================
// Router Details
// ============================================================

function loadRouterDetails(routerId, context) {
    const detailsPanel = $(`#${context}-router-details`);
    const infoDiv = $(`#${context}-router-info`);

    detailsPanel.show();
    infoDiv.html('<div class="loading-indicator"><div class="spinner-small"></div><span>Loading details...</span></div>');

    $.ajax({
        url: '/api/get-router-details',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            api_keys: AppState.apiKeys,
            router_id: routerId
        }),
        success: function(response) {
            if (response.success) {
                renderRouterDetails(response.router, context);
                if (context === 'source') {
                    AppState.sourceRouter = response.router;
                } else {
                    AppState.destRouter = response.router;
                }
            } else {
                infoDiv.html(`<div class="validation-error"><i class="fas fa-exclamation-circle"></i><span>${escapeHtml(response.message)}</span></div>`);
            }
        },
        error: function() {
            infoDiv.html('<div class="validation-error"><i class="fas fa-exclamation-circle"></i><span>Network error loading details</span></div>');
        }
    });
}

function renderRouterDetails(router, context) {
    const infoDiv = $(`#${context}-router-info`);

    const fields = [
        { label: 'Device Name', value: router.name, icon: 'fa-tag', color: '#4f46e5' },
        { label: 'Router ID', value: router.id, icon: 'fa-fingerprint', color: '#6b7280' },
        { label: 'State', value: router.state, icon: 'fa-power-off', color: router.state === 'online' ? '#059669' : '#dc2626' },
        { label: 'Model', value: extractProductName(router), icon: 'fa-microchip', color: '#7c3aed' },
        { label: 'Firmware', value: router.actual_firmware || 'N/A', icon: 'fa-code-branch', color: '#0284c7' },
        { label: 'MAC Address', value: router.mac, icon: 'fa-network-wired', color: '#475569' },
        { label: 'Serial Number', value: router.serial_number, icon: 'fa-barcode', color: '#92400e' },
        { label: 'IP Address', value: router.ipv4_address, icon: 'fa-globe', color: '#0891b2' },
        { label: 'Group', value: router.group_name, icon: 'fa-folder', color: '#ca8a04' },
        { label: 'Description', value: router.description, icon: 'fa-align-left', color: '#64748b' },
        { label: 'Asset ID', value: router.asset_id, icon: 'fa-id-card', color: '#be185d' },
        { label: 'Custom 1', value: router.custom1, icon: 'fa-pen', color: '#4338ca' }
    ];

    let html = '';
    fields.forEach(function(field) {
        const val = field.value || '';
        if (!val || val === 'N/A') return;

        html += `
            <div class="detail-row">
                <div class="detail-icon" style="color: ${field.color};">
                    <i class="fas ${field.icon}"></i>
                </div>
                <div class="detail-content">
                    <span class="detail-label">${field.label}</span>
                    <span class="detail-value">${escapeHtml(String(val))}</span>
                </div>
            </div>
        `;
    });

    if (!html) {
        html = '<div class="validation-warning"><i class="fas fa-exclamation-triangle"></i><span>Limited router information available</span></div>';
    }

    infoDiv.html(html);
}

function extractProductName(router) {
    if (router.product_name) return router.product_name;
    if (router.actual_product) return router.actual_product;

    const productInfo = router.product_info || '';
    if (productInfo && !productInfo.startsWith('http')) {
        return productInfo;
    }
    return 'N/A';
}

// ============================================================
// Source Device Confirmation
// ============================================================

function confirmSourceDevice() {
    if (!AppState.sourceRouter) {
        showToast('error', 'Please select a source router first');
        return;
    }

    // Use toast instead of persistent message
    showToast('success', `Source device confirmed: ${AppState.sourceRouter.name || AppState.sourceRouter.id}`);
    setNavStatus('source', true);
    updateProgress(2);
    enableNavStep('source-config-section');

    // Auto-collapse info boxes on this page
    collapseDefaultInfoBoxes('#source-device-section');

    setTimeout(function() {
        showSection('source-config-section');
        loadSourceConfig();
    }, 500);
}

// ============================================================
// Source Configuration
// ============================================================

function loadSourceConfig() {
    const configLoading = $('#config-loading');
    configLoading.show();
    $('#confirm-config-btn').prop('disabled', true);

    $.ajax({
        url: '/api/get-config',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            api_keys: AppState.apiKeys,
            router_id: AppState.sourceRouter.id,
            group_id: AppState.sourceGroupId
        }),
        success: function(response) {
            configLoading.hide();
            if (response.success) {
                AppState.sourceConfig = response.config;
                displayConfigurations(response.config);
                // Use toast instead of persistent status message
                showToast('success', 'Configurations retrieved successfully');
                $('#confirm-config-btn').prop('disabled', false);
            } else {
                showValidationStatus('config-validation-status', 'error',
                    response.message || 'Failed to retrieve configurations');
            }
        },
        error: function() {
            configLoading.hide();
            showValidationStatus('config-validation-status', 'error',
                'Network error retrieving configurations');
        }
    });
}

function displayConfigurations(config) {
    const groupConfig = config.group_config;
    if (groupConfig && Object.keys(groupConfig).length > 0) {
        $('#group-config-content').text(JSON.stringify(groupConfig, null, 2));
    } else {
        $('#group-config-content').text('No group-level configuration found.\n\nThis may indicate the group uses default settings.');
    }

    const deviceConfig = config.device_config;
    if (deviceConfig && ((Array.isArray(deviceConfig) && deviceConfig.length > 0) ||
        (!Array.isArray(deviceConfig) && Object.keys(deviceConfig).length > 0))) {
        $('#device-config-content').text(JSON.stringify(deviceConfig, null, 2));

        // Check for masked "*" values in device config
        const configStr = JSON.stringify(deviceConfig);
        if (configStr.indexOf('"*"') !== -1) {
            showMaskedFieldsWarning();
        } else {
            $('#masked-fields-warning').hide().html('');
        }
    } else {
        $('#device-config-content').text('No device-level configuration overrides found.\n\nThis device may be using only group-level configuration.');
        $('#masked-fields-warning').hide().html('');
    }

    // Auto-collapse the default info boxes on this page
    collapseDefaultInfoBoxes('#source-config-section');
}

function showMaskedFieldsWarning() {
    const html = `
        <div class="info-box info-box-warning collapsible">
            <div class="info-box-header" onclick="toggleCollapsible(this)">
                <div class="info-box-header-left">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span class="info-box-title">Masked Fields Cannot Be Migrated</span>
                </div>
                <i class="fas fa-chevron-down info-box-chevron"></i>
            </div>
            <div class="info-box-body">
                <span>Device-level configuration fields whose value is <strong>"*"</strong> (masked) cannot be migrated. This includes sensitive fields such as admin passwords, IPSec pre-shared keys, WPA PSK, VPN credentials, and SNMP community strings. These must be manually reconfigured on the destination device.</span>
            </div>
        </div>
    `;
    $('#masked-fields-warning').html(html).show();
}

// ============================================================
// Destination Validation
// ============================================================

function validateDestination() {
    if (!AppState.destRouter) {
        showToast('error', 'Please select a destination router first');
        return;
    }

    if (!AppState.sourceRouter) {
        showToast('error', 'Source router not set. Please go back and select a source device.');
        return;
    }

    showLoading('Validating destination device compatibility...');

    $.ajax({
        url: '/api/validate-destination',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            api_keys: AppState.apiKeys,
            source_router: AppState.sourceRouter,
            dest_router_id: AppState.destRouter.id
        }),
        success: function(response) {
            hideLoading();
            if (response.success) {
                displayCompatibilityResults(response.validation);
            } else {
                showValidationStatus('dest-validation-status', 'error',
                    response.message || 'Validation failed');
            }
        },
        error: function() {
            hideLoading();
            showValidationStatus('dest-validation-status', 'error',
                'Network error during validation');
        }
    });
}

function displayCompatibilityResults(validation) {
    const resultsDiv = $('#dest-compatibility-results');
    // Clear any previous validation status
    $('#dest-validation-status').html('');
    let html = '';

    // Show errors persistently (these block progress)
    if (validation.errors && validation.errors.length > 0) {
        validation.errors.forEach(function(err) {
            html += `<div class="compat-error"><i class="fas fa-times-circle"></i><span>${escapeHtml(err)}</span></div>`;
        });
        setNavStatus('dest', false);
        showToast('error', 'Destination device failed compatibility checks');
    }

    // Show success as toast only (no persistent message)
    if (validation.valid) {
        setNavStatus('dest', true);
        updateProgress(4);
        showToast('success', 'Destination device is compatible');

        // Enable next step
        enableNavStep('dest-config-section');
        setTimeout(function() {
            showSection('dest-config-section');
            buildMaskedFieldsUI();
        }, 800);
    }

    resultsDiv.html(html);

    // Auto-collapse default info boxes now that results are showing
    collapseDefaultInfoBoxes('#dest-device-section');
}

// ============================================================
// Destination Config - Masked Field Resolution
// ============================================================

/**
 * Scan the source device config for masked ("*") fields and build the
 * resolution UI allowing the user to choose how to handle each one.
 */
function buildMaskedFieldsUI() {
    const deviceConfig = AppState.sourceConfig ? AppState.sourceConfig.device_config : null;

    if (!deviceConfig) {
        $('#masked-fields-table-container').html(
            '<div class="empty-state"><i class="fas fa-check-circle" style="color: var(--success-color);"></i><p>No device-level configuration to review</p></div>'
        );
        return;
    }

    // Find all paths with "*" values
    const maskedPaths = [];
    findMaskedFields(deviceConfig, '', maskedPaths);

    AppState.maskedFields = maskedPaths;

    if (maskedPaths.length === 0) {
        $('#masked-fields-table-container').html(
            '<div class="empty-state"><i class="fas fa-check-circle" style="color: var(--success-color);"></i><p>No masked fields detected in the device configuration. All fields can be migrated as-is.</p></div>'
        );
        // Show warning placeholder with info
        $('#dest-config-masked-warning').html('');
        return;
    }

    // Show warning at top
    $('#dest-config-masked-warning').html(`
        <div class="info-box info-box-warning collapsible">
            <div class="info-box-header" onclick="toggleCollapsible(this)">
                <div class="info-box-header-left">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span class="info-box-title">${maskedPaths.length} Masked Field${maskedPaths.length > 1 ? 's' : ''} Detected</span>
                </div>
                <i class="fas fa-chevron-down info-box-chevron"></i>
            </div>
            <div class="info-box-body">
                <span>The following fields contain encrypted values that cannot be read from the source device. Choose how to handle each field in the destination configuration.</span>
            </div>
        </div>
    `);

    // Build table
    let html = '<div class="masked-fields-table"><table><thead><tr>';
    html += '<th>Configuration Path</th>';
    html += '<th>Resolution</th>';
    html += '<th>Custom Value</th>';
    html += '</tr></thead><tbody>';

    maskedPaths.forEach(function(item, idx) {
        const destSerial = AppState.destRouter ? (AppState.destRouter.serial_number || '') : '';
        html += `
            <tr data-idx="${idx}">
                <td class="masked-field-path"><code>${escapeHtml(item.path)}</code></td>
                <td>
                    <select class="form-select masked-resolution-select" data-idx="${idx}">
                        <option value="remove">Remove from config (inherit group/default)</option>
                        <option value="blank">Set to blank ("")</option>
                        <option value="serial">Use destination serial (${escapeHtml(destSerial)})</option>
                        <option value="custom">Custom value</option>
                    </select>
                </td>
                <td>
                    <div class="input-with-toggle">
                        <input type="password" class="form-input masked-custom-input" data-idx="${idx}" placeholder="Enter value..." disabled>
                        <button type="button" class="password-toggle masked-custom-toggle" data-idx="${idx}" title="Show/Hide value">
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table></div>';
    $('#masked-fields-table-container').html(html);

    // Bind change events for resolution selects
    $('.masked-resolution-select').change(function() {
        const idx = $(this).data('idx');
        const val = $(this).val();
        const customInput = $(`.masked-custom-input[data-idx="${idx}"]`);

        if (val === 'custom') {
            customInput.prop('disabled', false).focus();
        } else {
            customInput.prop('disabled', true).val('');
        }
    });

    // Bind show/hide toggle for custom value inputs
    $('.masked-custom-toggle').click(function() {
        const idx = $(this).data('idx');
        const input = $(`.masked-custom-input[data-idx="${idx}"]`);
        const icon = $(this).find('i');

        if (input.attr('type') === 'password') {
            input.attr('type', 'text');
            icon.removeClass('fa-eye').addClass('fa-eye-slash');
        } else {
            input.attr('type', 'password');
            icon.removeClass('fa-eye-slash').addClass('fa-eye');
        }
    });
}

/**
 * Recursively find all fields with value "*" in a config object.
 */
function findMaskedFields(obj, prefix, results) {
    if (Array.isArray(obj)) {
        obj.forEach(function(item, idx) {
            findMaskedFields(item, prefix + '[' + idx + ']', results);
        });
    } else if (obj && typeof obj === 'object') {
        Object.keys(obj).forEach(function(key) {
            const newPath = prefix ? prefix + '.' + key : key;
            const val = obj[key];
            if (val === '*') {
                results.push({ path: newPath, resolution: 'blank', customValue: '' });
            } else if (typeof val === 'object' && val !== null) {
                findMaskedFields(val, newPath, results);
            }
        });
    }
}

/**
 * Confirm the masked field resolutions and build the resolved config.
 */
function confirmDestConfig() {
    const deviceConfig = AppState.sourceConfig ? AppState.sourceConfig.device_config : null;

    if (!deviceConfig) {
        showToast('error', 'No device configuration available');
        return;
    }

    // Read resolutions from the UI
    const resolutions = {};
    let hasError = false;

    AppState.maskedFields.forEach(function(item, idx) {
        const selectVal = $(`.masked-resolution-select[data-idx="${idx}"]`).val();
        const customVal = $(`.masked-custom-input[data-idx="${idx}"]`).val();

        if (selectVal === 'custom' && !customVal) {
            hasError = true;
            showToast('error', `Please enter a custom value for: ${item.path}`);
        }

        resolutions[item.path] = {
            resolution: selectVal,
            customValue: customVal || ''
        };
    });

    if (hasError) return;

    // Build the resolved config by deep-cloning and applying resolutions
    const resolvedConfig = JSON.parse(JSON.stringify(deviceConfig));
    const destSerial = AppState.destRouter ? (AppState.destRouter.serial_number || '') : '';
    const removedFields = [];

    Object.keys(resolutions).forEach(function(path) {
        const res = resolutions[path];
        let newValue;

        switch (res.resolution) {
            case 'remove':
                // Remove the field entirely — device inherits group/default
                newValue = undefined;
                removedFields.push(path);
                break;
            case 'blank':
                newValue = '';
                break;
            case 'serial':
                newValue = destSerial;
                break;
            case 'custom':
                newValue = res.customValue;
                break;
        }

        applyValueAtPath(resolvedConfig, path, newValue);
    });

    AppState.removedFields = removedFields;

    // If ECM API ID checkbox is checked, add it to SDK appdata in the config
    if ($('#add-ecm-api-id-checkbox').is(':checked') && AppState.apiKeys) {
        const ecmApiId = AppState.apiKeys['X-ECM-API-ID'] || '';
        if (ecmApiId) {
            // Ensure system.sdk.appdata path exists and add the value
            if (!resolvedConfig.system) resolvedConfig.system = {};
            if (!resolvedConfig.system.sdk) resolvedConfig.system.sdk = {};
            if (!resolvedConfig.system.sdk.appdata) resolvedConfig.system.sdk.appdata = {};

            // Add as appdata entry with key 'rma_wizard' including timestamp
            const timestamp = new Date().toISOString();
            const appdataId = 'rma-wizard-' + Date.now();
            resolvedConfig.system.sdk.appdata[appdataId] = {
                '_id_': appdataId,
                'name': 'rma_wizard',
                'value': ecmApiId + '|' + timestamp
            };
        }
    }

    AppState.resolvedConfig = resolvedConfig;

    setNavStatus('dest-config', true);
    updateProgress(5);
    enableNavStep('apply-section');
    showToast('success', 'Destination configuration confirmed');
    collapseDefaultInfoBoxes('#dest-config-section');

    setTimeout(function() {
        showSection('apply-section');
        buildApplySummary();
    }, 500);
}

/**
 * Set or remove a value at a dot-notation path in a nested object.
 * Supports array indices like [0].
 */
function applyValueAtPath(obj, path, value) {
    // Parse path: convert [n] to .n, split on dots, remove empty parts
    const parts = path.replace(/\[(\d+)\]/g, '.$1').split('.').filter(function(p) { return p !== ''; });
    let current = obj;

    for (let i = 0; i < parts.length - 1; i++) {
        const key = parts[i];
        // For arrays, access by numeric index
        if (Array.isArray(current)) {
            current = current[parseInt(key)];
        } else {
            current = current[key];
        }
        if (current === undefined || current === null) return;
    }

    const lastKey = parts[parts.length - 1];
    if (value === undefined) {
        // Exclude: delete the field
        if (Array.isArray(current)) {
            current.splice(parseInt(lastKey), 1);
        } else {
            delete current[lastKey];
        }
    } else {
        if (Array.isArray(current)) {
            current[parseInt(lastKey)] = value;
        } else {
            current[lastKey] = value;
        }
    }
}

// ============================================================
// Apply Migration
// ============================================================

function buildApplySummary() {
    const srcName = AppState.sourceRouter ? (AppState.sourceRouter.name || AppState.sourceRouter.id) : 'Unknown';
    const dstName = AppState.destRouter ? (AppState.destRouter.name || AppState.destRouter.id) : 'Unknown';
    const groupName = getGroupNameById(AppState.sourceGroupId) || `Group ${AppState.sourceGroupId}`;
    const maskedCount = AppState.maskedFields.length;

    let html = '<div class="apply-summary-list">';
    html += `<div class="detail-row"><div class="detail-icon" style="color: #dc2626;"><i class="fas fa-server"></i></div><div class="detail-content"><span class="detail-label">Source Device</span><span class="detail-value">${escapeHtml(srcName)}</span></div></div>`;
    html += `<div class="detail-row"><div class="detail-icon" style="color: #059669;"><i class="fas fa-exchange-alt"></i></div><div class="detail-content"><span class="detail-label">Destination Device</span><span class="detail-value">${escapeHtml(dstName)}</span></div></div>`;
    html += `<div class="detail-row"><div class="detail-icon" style="color: #ca8a04;"><i class="fas fa-folder"></i></div><div class="detail-content"><span class="detail-label">Move Destination To Group</span><span class="detail-value">${escapeHtml(groupName)}</span></div></div>`;
    html += `<div class="detail-row"><div class="detail-icon" style="color: #7c3aed;"><i class="fas fa-edit"></i></div><div class="detail-content"><span class="detail-label">Masked Fields Resolved</span><span class="detail-value">${maskedCount} field${maskedCount !== 1 ? 's' : ''}</span></div></div>`;
    html += '</div>';

    $('#apply-summary').html(html);
}

function getGroupNameById(groupId) {
    const group = AppState.groups.find(function(g) { return String(g.id) === String(groupId); });
    return group ? group.name : null;
}

function applyMigration() {
    if (!AppState.resolvedConfig && !AppState.sourceConfig) {
        showToast('error', 'No configuration prepared. Go back and confirm destination config.');
        return;
    }

    // Show confirmation modal
    const destName = AppState.destRouter ? (AppState.destRouter.name || AppState.destRouter.id) : 'Unknown';
    const groupName = getGroupNameById(AppState.sourceGroupId) || `Group ${AppState.sourceGroupId}`;
    showConfirmModal(
        `This will move "${destName}" into group "${groupName}" and apply the source device configuration. This cannot be easily undone. Continue?`,
        function() {
            doApplyMigration();
        }
    );
}

function doApplyMigration() {
    // Clear any previous error/warning messages
    $('#apply-validation-status').html('');

    const configToApply = AppState.resolvedConfig || AppState.sourceConfig.device_config;

    showLoading('Applying migration — moving device and patching configuration...');

    $.ajax({
        url: '/api/apply-migration',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            api_keys: AppState.apiKeys,
            source_router: AppState.sourceRouter,
            dest_router_id: AppState.destRouter.id,
            source_group_id: AppState.sourceGroupId,
            device_config: configToApply,
            masked_field_resolutions: {}
        }),
        success: function(response) {
            hideLoading();
            if (response.success) {
                setNavStatus('apply', true);
                updateProgress(6);
                enableNavStep('verify-section');
                showToast('success', 'Migration applied successfully');
                collapseDefaultInfoBoxes('#apply-section');

                // Show fields that need manual update
                showRemovedFieldsNotice();

                // Auto-advance to verification after a delay
                setTimeout(function() {
                    showSection('verify-section');
                    setTimeout(verifyMigration, 5000);
                }, 2000);
            } else {
                showValidationStatus('apply-validation-status', 'error',
                    response.message || 'Failed to apply migration');
                setNavStatus('apply', false);
                showToast('error', 'Migration failed');
            }
        },
        error: function(xhr) {
            hideLoading();
            const detail = xhr.responseJSON ? xhr.responseJSON.message : '';
            showValidationStatus('apply-validation-status', 'error',
                detail || 'Network error applying migration');
            showToast('error', 'Network error during migration');
        }
    });
}

/**
 * Show a notice listing fields that were removed and need manual configuration.
 */
function showRemovedFieldsNotice() {
    if (!AppState.removedFields || AppState.removedFields.length === 0) return;

    let html = '<div class="compat-warning" style="margin-top: 1.5rem;"><i class="fas fa-exclamation-triangle"></i><div>';
    html += '<strong>The following fields were removed from the config and must be manually configured on the destination device:</strong>';
    html += '<ul style="margin: 0.5rem 0 0 1rem; font-size: 0.8125rem;">';
    AppState.removedFields.forEach(function(path) {
        html += `<li><code style="background: rgba(217,119,6,0.1); padding: 0.125rem 0.375rem; border-radius: 3px;">${escapeHtml(path)}</code></li>`;
    });
    html += '</ul></div></div>';

    $('#apply-validation-status').html(html);
}

// ============================================================
// Verification
// ============================================================

function verifyMigration() {
    const verifyLoading = $('#verify-loading');
    const resultsDiv = $('#verify-results');
    const detailsDiv = $('#verify-details');

    verifyLoading.show();
    resultsDiv.html('');
    detailsDiv.hide();
    $('#reverify-btn').hide();

    $.ajax({
        url: '/api/verify-migration',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            api_keys: AppState.apiKeys,
            dest_router_id: AppState.destRouter.id,
            expected_config: AppState.resolvedConfig || AppState.sourceConfig.device_config
        }),
        success: function(response) {
            verifyLoading.hide();
            if (response.success) {
                displayVerificationResults(response.verification);
            } else {
                showValidationStatus('verify-validation-status', 'error',
                    response.message || 'Verification failed');
                $('#reverify-btn').show();
            }
        },
        error: function() {
            verifyLoading.hide();
            showValidationStatus('verify-validation-status', 'error',
                'Network error during verification');
            $('#reverify-btn').show();
        }
    });
}

function displayVerificationResults(verification) {
    const resultsDiv = $('#verify-results');
    let html = '';

    // Clear any auto-poll timer
    if (AppState._verifyTimer) {
        clearTimeout(AppState._verifyTimer);
        AppState._verifyTimer = null;
    }

    // 1. Device group move confirmation (always show)
    html += `<div class="compat-success"><i class="fas fa-check-circle"></i><span>Destination device has been moved to the source group. Group-level configuration is inherited automatically.</span></div>`;

    // 2. Sync status
    if (verification.synched) {
        html += `<div class="compat-success"><i class="fas fa-check-circle"></i><span>Configuration sync complete. The device has the correct configuration applied.</span></div>`;
        setNavStatus('verify', true);
        updateProgress(7);
        showToast('success', 'Migration verification complete');
    } else {
        html += `<div class="compat-info"><i class="fas fa-clock"></i><span>Configuration has not yet synced to the device. Auto-checking every 10 seconds...</span></div>`;
        // Auto re-verify in 10 seconds
        AppState._verifyTimer = setTimeout(function() {
            verifyMigration();
        }, 10000);
    }

    // 3. Errors (if any)
    if (verification.errors && verification.errors.length > 0) {
        verification.errors.forEach(function(err) {
            html += `<div class="compat-error"><i class="fas fa-times-circle"></i><span>${escapeHtml(err)}</span></div>`;
        });
        setNavStatus('verify', false);
    }

    // 4. Warnings (if any, but NOT the generic info messages once synced)
    if (verification.warnings && verification.warnings.length > 0) {
        verification.warnings.forEach(function(warn) {
            html += `<div class="compat-warning"><i class="fas fa-exclamation-triangle"></i><span>${escapeHtml(warn)}</span></div>`;
        });
    }

    // 5. Fields needing manual update (always last)
    if (AppState.removedFields && AppState.removedFields.length > 0) {
        html += '<div class="compat-warning"><i class="fas fa-exclamation-triangle"></i><div>';
        html += '<strong>The following fields must be manually configured on the destination device:</strong>';
        html += '<ul style="margin: 0.5rem 0 0 1rem; font-size: 0.8125rem;">';
        AppState.removedFields.forEach(function(path) {
            html += `<li><code style="background: rgba(217,119,6,0.1); padding: 0.125rem 0.375rem; border-radius: 3px;">${escapeHtml(path)}</code></li>`;
        });
        html += '</ul></div></div>';
    }

    resultsDiv.html(html);
    $('#reverify-btn').show();

    // Show sync details
    const detailsDiv = $('#verify-details');
    const infoList = $('#verify-info-list');
    let detailHtml = '';

    detailHtml += `
        <div class="detail-row">
            <div class="detail-icon" style="color: ${verification.synched ? '#059669' : '#d97706'};">
                <i class="fas ${verification.synched ? 'fa-check-circle' : 'fa-clock'}"></i>
            </div>
            <div class="detail-content">
                <span class="detail-label">Sync Status</span>
                <span class="detail-value">${verification.synched ? 'Synched' : 'Pending sync — re-checking automatically'}</span>
            </div>
        </div>
    `;

    detailHtml += `
        <div class="detail-row">
            <div class="detail-icon" style="color: ${verification.suspended ? '#dc2626' : '#059669'};">
                <i class="fas ${verification.suspended ? 'fa-pause-circle' : 'fa-play-circle'}"></i>
            </div>
            <div class="detail-content">
                <span class="detail-label">Sync Suspended</span>
                <span class="detail-value">${verification.suspended ? 'Yes — config may not apply until resumed' : 'No — sync active'}</span>
            </div>
        </div>
    `;

    infoList.html(detailHtml);
    detailsDiv.show();
}

// ============================================================
// UI Helpers
// ============================================================

function showValidationStatus(elementId, type, message) {
    const icon = type === 'success' ? 'fa-check-circle' :
                 type === 'error' ? 'fa-exclamation-circle' :
                 'fa-exclamation-triangle';
    const cls = `validation-${type}`;

    $(`#${elementId}`).html(
        `<div class="${cls}"><i class="fas ${icon}"></i><span>${escapeHtml(message)}</span></div>`
    );
}

function showLoading(message) {
    $('#loading-message').text(message || 'Processing...');
    $('#loading-overlay').show();
}

function hideLoading() {
    $('#loading-overlay').hide();
}

function showToast(type, message) {
    const toast = $(`
        <div class="toast toast-${type}">
            <i class="fas ${type === 'success' ? 'fa-check-circle' :
                           type === 'error' ? 'fa-exclamation-circle' :
                           type === 'warning' ? 'fa-exclamation-triangle' :
                           'fa-info-circle'}"></i>
            <span>${escapeHtml(message)}</span>
        </div>
    `);

    $('#toast-container').append(toast);

    setTimeout(function() {
        toast.fadeOut(300, function() { $(this).remove(); });
    }, 4000);
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

// ============================================================
// Collapsible Info Boxes
// ============================================================

function toggleCollapsible(headerEl) {
    const infoBox = $(headerEl).closest('.collapsible');
    infoBox.toggleClass('collapsed');
}

function closeHelpModal() {
    $('#help-modal').fadeOut(200);
}

function showConfirmModal(message, onConfirm) {
    $('#confirm-modal-message').text(message);
    $('#confirm-modal').fadeIn(200);
    $('#confirm-modal-ok').off('click').on('click', function() {
        closeConfirmModal(false);
        onConfirm();
    });
}

function closeConfirmModal() {
    $('#confirm-modal').fadeOut(200);
}

/**
 * Auto-collapse all default (non-dynamic) info boxes within a section.
 * Called when validation results or new messages appear to reduce clutter.
 */
function collapseDefaultInfoBoxes(sectionSelector) {
    $(sectionSelector).find('.info-box.collapsible').not('.collapsed').addClass('collapsed');
}
