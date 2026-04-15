(function () {
    const card = document.getElementById("card");
    const fileInput = document.getElementById("file-input");
    const chooseBtn = document.getElementById("choose-file-btn");

    const runningFilename = document.getElementById("running-filename");
    const runningStatus = document.getElementById("running-status");

    const doneFilename = document.getElementById("done-filename");
    const downloadLink = document.getElementById("download-link");
    const openFolderBtn = document.getElementById("open-folder-btn");
    const resetBtnDone = document.getElementById("reset-btn-done");

    const failedFilename = document.getElementById("failed-filename");
    const failedMessage = document.getElementById("failed-message");
    const failedNextStep = document.getElementById("failed-next-step");
    const resetBtnFailed = document.getElementById("reset-btn-failed");
    const openFolderBtnFailed = document.getElementById("open-folder-btn-failed");

    const openFolderFooter = document.getElementById("open-folder-footer");

    const POLL_INTERVAL_MS = 1000;
    const STATUS_TEXTS = {
        queued: "변환 준비 중…",
        running: "변환 중… (Java/OpenDataLoader 구동)",
    };

    let pollTimer = null;

    const FAILURE_HINTS = {
        java_missing: "Java 11 이상을 설치하거나 PATH에 Java가 등록되어 있는지 확인해 주세요.",
        java_version_too_low: "Java를 11 이상 버전으로 업데이트한 뒤 다시 시도해 주세요.",
        engine_missing: "installer\\install.ps1 를 다시 실행해 설치를 완료해 주세요.",
        output_dir_unavailable: "결과 폴더 경로와 쓰기 권한을 확인해 주세요.",
        output_write_failed: "결과 폴더 경로와 쓰기 권한을 확인해 주세요.",
        staging_failed: "디스크 공간과 임시 폴더 쓰기 권한을 확인해 주세요.",
        result_missing: "다른 PDF로 다시 시도해 보세요.",
        engine_failed: "원본 PDF가 정상적으로 열리는지 확인하고 다른 PDF로 다시 시도해 보세요.",
        internal_error: "앱을 다시 실행한 뒤 다시 시도해 주세요.",
    };

    function setState(state) {
        card.dataset.state = state;
    }

    function resetToIdle() {
        if (pollTimer) {
            clearTimeout(pollTimer);
            pollTimer = null;
        }
        fileInput.value = "";
        setState("idle");
    }

    function isPdf(file) {
        if (!file) return false;
        const name = (file.name || "").toLowerCase();
        return name.endsWith(".pdf");
    }

    async function uploadFile(file) {
        runningFilename.textContent = file.name;
        runningStatus.textContent = STATUS_TEXTS.queued;
        setState("running");

        const formData = new FormData();
        formData.append("file", file);

        let response;
        try {
            response = await fetch("/api/convert", { method: "POST", body: formData });
        } catch (err) {
            showFailure(
                file.name,
                "서버에 연결할 수 없습니다. 앱이 실행 중인지 확인해 주세요.",
                "앱 창이 꺼져 있다면 바탕화면의 QmapLoader 아이콘으로 다시 실행해 주세요.",
            );
            return;
        }

        if (!response.ok) {
            let detail = "업로드에 실패했습니다.";
            try {
                const body = await response.json();
                if (body && body.detail) detail = body.detail;
            } catch (_) { /* ignore */ }
            showFailure(file.name, detail, "같은 문제가 반복되면 앱을 다시 실행한 뒤 다시 시도해 주세요.");
            return;
        }

        const body = await response.json();
        pollJob(body.job_id, file.name);
    }

    function pollJob(jobId, originalName) {
        const tick = async () => {
            let response;
            try {
                response = await fetch(`/api/jobs/${jobId}`);
            } catch (err) {
                showFailure(
                    originalName,
                    "작업 상태를 확인할 수 없습니다.",
                    "네트워크 연결 또는 앱 상태를 확인한 뒤 다시 시도해 주세요.",
                );
                return;
            }

            if (!response.ok) {
                showFailure(
                    originalName,
                    "작업 정보를 찾을 수 없습니다.",
                    "같은 PDF로 다시 업로드해 주세요.",
                );
                return;
            }

            const job = await response.json();
            if (job.status === "queued" || job.status === "running") {
                runningStatus.textContent = STATUS_TEXTS[job.status] || "변환 중…";
                pollTimer = setTimeout(tick, POLL_INTERVAL_MS);
                return;
            }

            if (job.status === "done") {
                showSuccess(jobId, job.markdown_filename || originalName);
                return;
            }

            if (job.status === "failed") {
                showFailure(
                    originalName,
                    job.user_error || "변환에 실패했습니다.",
                    job.next_step || FAILURE_HINTS[job.error_code] || "파일을 다시 업로드해 주세요.",
                );
                return;
            }

            showFailure(originalName, "알 수 없는 상태입니다.", "파일을 다시 업로드해 주세요.");
        };

        tick();
    }

    function showSuccess(jobId, markdownFilename) {
        doneFilename.textContent = markdownFilename;
        downloadLink.href = `/api/jobs/${jobId}/result`;
        downloadLink.setAttribute("download", markdownFilename);
        setState("done");
    }

    function showFailure(filename, message, nextStep = "") {
        failedFilename.textContent = filename;
        failedMessage.textContent = message;
        failedNextStep.textContent = nextStep;
        failedNextStep.hidden = !nextStep;
        setState("failed");
    }

    function handleFile(file) {
        if (!isPdf(file)) {
            showFailure(file ? file.name : "(알 수 없음)", "PDF 파일만 업로드할 수 있습니다.");
            return;
        }
        uploadFile(file);
    }

    // Idle card → click to choose
    card.addEventListener("click", (e) => {
        if (card.dataset.state !== "idle") return;
        if (e.target.closest("button, a, input")) return;
        fileInput.click();
    });

    chooseBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    fileInput.addEventListener("change", () => {
        const file = fileInput.files && fileInput.files[0];
        if (file) handleFile(file);
    });

    // Drag & drop
    ["dragenter", "dragover"].forEach((evt) => {
        card.addEventListener(evt, (e) => {
            if (card.dataset.state !== "idle") return;
            e.preventDefault();
            card.classList.add("is-dragover");
        });
    });
    ["dragleave", "dragend", "drop"].forEach((evt) => {
        card.addEventListener(evt, (e) => {
            e.preventDefault();
            card.classList.remove("is-dragover");
        });
    });
    card.addEventListener("drop", (e) => {
        if (card.dataset.state !== "idle") return;
        const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
        if (file) handleFile(file);
    });

    // Window-level dragover to prevent browser navigation when dropping outside card
    window.addEventListener("dragover", (e) => e.preventDefault());
    window.addEventListener("drop", (e) => e.preventDefault());

    // Actions
    resetBtnDone.addEventListener("click", resetToIdle);
    resetBtnFailed.addEventListener("click", resetToIdle);

    async function openOutputFolder() {
        try {
            await fetch("/api/open-folder", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({}),
            });
        } catch (_) { /* ignore */ }
    }

    openFolderBtn.addEventListener("click", openOutputFolder);
    openFolderBtnFailed.addEventListener("click", openOutputFolder);
    openFolderFooter.addEventListener("click", openOutputFolder);
})();
