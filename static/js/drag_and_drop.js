document.addEventListener('DOMContentLoaded', function() {
    const dropZones = document.querySelectorAll('.drag-and-drop-zone');

    dropZones.forEach(zone => {
        const input = zone.querySelector('input[type="file"]');
        const dropArea = zone.querySelector('.drop-area');
        const fileDetails = document.getElementById(`${input.id}-file-details`);
        const fileNameElement = document.getElementById(`${input.id}-file-name`);
        const fileLinkElement = document.getElementById(`${input.id}-file-link`);

        function updateFileDetails(file) {
            const fileName = file.name;
            const fileUrl = URL.createObjectURL(file);

            fileNameElement.textContent = fileName;
            fileLinkElement.href = fileUrl;
            fileLinkElement.classList.remove('hidden');
            fileDetails.classList.remove('hidden');
        }

        // Handle drag over
        zone.addEventListener('dragover', (event) => {
            event.preventDefault();
            zone.classList.add('drag-over');
            dropArea.classList.add('drag-over');
        });

        // Handle drag leave
        zone.addEventListener('dragleave', () => {
            zone.classList.remove('drag-over');
            dropArea.classList.remove('drag-over');
        });

        // Handle drop
        zone.addEventListener('drop', (event) => {
            event.preventDefault();
            zone.classList.remove('drag-over');
            dropArea.classList.remove('drag-over');

            const files = event.dataTransfer.files;
            if (files.length > 0) {
                input.files = files;
                updateFileDetails(files[0]);
            }
        });

        // Handle file input click
        dropArea.addEventListener('click', () => {
            input.click();
        });

        // Handle file input change
        input.addEventListener('change', () => {
            if (input.files.length > 0) {
                updateFileDetails(input.files[0]);
            }
        });

        // If there's an initial file, show its details
        if (input.dataset.initial) {
            fileNameElement.textContent = input.dataset.initialName;
            fileLinkElement.href = input.dataset.initialUrl;
            fileLinkElement.classList.remove('hidden');
            fileDetails.classList.remove('hidden');
        }
    });
});
