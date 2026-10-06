function setFileName(name) {
    const base = name.trim().replace(/\.set$/i, "")
        .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_")
        .replace(/[. ]+$/g, "").slice(0, 120) || "Meu setup";
    return `${/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(base) ? `_${base}` : base}.set`;
}

function serializeSetupSet(roots) {
    const pages = {};
    let name = "Meu setup";
    for (const [page, root] of roots) {
        restoreSetup(root, page);
        const nameControl = root.querySelector("[data-setup-name]");
        if (nameControl) {
            name = nameControl.value.trim() || name;
            root.querySelector("[data-setup-magic]").value = magicNumberFromName(nameControl.value);
        }
        // Keep every control in storage order, including optimization ranges and
        // inactive options, so no configuration is lost during export.
        pages[page] = setupControls(root).map((control, index) => ({
            key: control.name || control.id || `${page}_${index}`,
            value: control.value,
            checked: control.checked,
        }));
    }
    return {
        filename: setFileName(name),
        contents: JSON.stringify({
            format: "geraset",
            version: 1,
            name,
            pages,
        }, null, 2) + "\n",
    };
}

async function writeSetupSet(handle, contents) {
    const writable = await handle.createWritable();
    try {
        await writable.write(contents);
        await writable.close();
    } catch (error) {
        try { await writable.abort(); } catch { /* Preserve the original error. */ }
        throw error;
    }
}

function downloadSetupSet(file) {
    const url = URL.createObjectURL(new Blob([file.contents], {type: "application/json;charset=utf-8"}));
    const link = document.createElement("a");
    link.href = url;
    link.download = file.filename;
    document.body.appendChild(link);
    try { link.click(); }
    finally {
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 60000);
    }
}

async function bindSetExport() {
    const button = document.querySelector("[data-export-set]");
    const status = document.querySelector("[data-export-status]");
    if (!button || !status) return;
    let roots;
    const supportsPicker = typeof window.showSaveFilePicker === "function";
    const readyMessage = supportsPicker
        ? "Escolha a pasta e o nome do arquivo ao exportar."
        : "A exportação usa o download do navegador. Para escolher a pasta, ative a opção de perguntar onde salvar os downloads.";

    async function loadPages() {
        const entries = await Promise.all(["inicio", "indicadores", "gestao"].map(async page => {
            const response = await fetch(`/${page}`);
            if (!response.ok) throw new Error("Falha ao carregar o set");
            const root = new DOMParser().parseFromString(await response.text(), "text/html");
            if (!root.querySelector(`[data-page="${page}"]`)) throw new Error("Página inválida");
            return [page, root];
        }));
        return new Map(entries);
    }

    button.addEventListener("click", async () => {
        button.disabled = true;
        if (!roots) {
            try {
                status.textContent = "Preparando exportação...";
                roots = await loadPages();
                status.textContent = readyMessage;
                button.textContent = "Exportar set";
            } catch {
                status.textContent = "Não foi possível carregar o set. Clique para tentar novamente.";
            } finally { button.disabled = false; }
            return;
        }
        try {
            const file = serializeSetupSet(roots);
            if (supportsPicker) {
                // Open directly from the click; awaiting a fetch first would
                // lose the user activation required by the browser.
                const handle = await window.showSaveFilePicker({
                    id: "geraset-export",
                    suggestedName: file.filename,
                    types: [{description: "Set do GeraSet", accept: {"application/json": [".set"]}}],
                    excludeAcceptAllOption: true,
                });
                status.textContent = "Salvando set...";
                await writeSetupSet(handle, file.contents);
                status.textContent = `Set salvo: ${handle.name || file.filename}`;
            } else {
                downloadSetupSet(file);
                status.textContent = `Download iniciado: ${file.filename}. O local segue a configuração do navegador.`;
            }
        } catch (error) {
            status.textContent = error.name === "AbortError"
                ? "Exportação cancelada."
                : "Não foi possível salvar o set. Tente novamente e confira a permissão da pasta escolhida.";
        } finally { button.disabled = false; }
    });

    try {
        roots = await loadPages();
        status.textContent = readyMessage;
    } catch {
        button.textContent = "Tentar novamente";
        status.textContent = "Não foi possível carregar o set. Clique para tentar novamente.";
    } finally { button.disabled = false; }
}

document.addEventListener("DOMContentLoaded", bindSetExport);
