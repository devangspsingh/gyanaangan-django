/**
 * Banner Image Cropper - Interactive cropping tool for desktop (1600x324) and mobile (1600x648)
 * Opens modal immediately when image is uploaded
 * Uses Cropper.js library
 */

(function() {
    'use strict';

    let cropper = null;
    let currentFile = null;
    let currentFieldType = 'desktop'; // 'desktop' or 'mobile'
    const aspectRatios = {
        desktop: 1600 / 324,  // 4.938...
        mobile: 1600 / 648    // 2.469...
    };
    const dimensions = {
        desktop: { width: 1600, height: 324 },
        mobile: { width: 1600, height: 648 }
    };

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        setupImageFieldWatchers();
        setupExistingImageCroppers();
    }

    // Create modal HTML
    function createCropperModal(fieldType) {
        const modal = document.createElement('div');
        modal.id = 'banner-crop-modal';
        const targetRatio = aspectRatios[fieldType];
        const targetDims = dimensions[fieldType];
        const title = fieldType === 'desktop' ? 'Desktop' : 'Mobile';
        const bgColor = fieldType === 'desktop' ? '#2196F3' : '#FF9800';
        
        modal.style.cssText = `
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            z-index: 999999;
            overflow: auto;
        `;

        modal.innerHTML = `
            <div style="max-width: 1200px; margin: 20px auto; padding: 20px; background: white; border-radius: 8px; position: relative;">
                <!-- Header -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid ${bgColor};">
                    <h2 style="margin: 0; color: ${bgColor};">✂️ Crop ${title} Image to ${targetDims.width}x${targetDims.height} (${targetRatio.toFixed(2)}:1)</h2>
                    <button id="modal-close-btn" type="button" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold;">
                        ✕ Cancel
                    </button>
                </div>

                <!-- Cropper Area -->
                <div style="margin-bottom: 20px; max-height: 600px; overflow: hidden;">
                    <img id="modal-crop-image" style="max-width: 100%; display: block;" />
                </div>

                <!-- Controls -->
                <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 15px; padding: 15px; background: #f8f9fa; border-radius: 4px;">
                    <button type="button" id="modal-zoom-in" class="crop-btn" style="background: ${bgColor}; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">
                        🔍+ Zoom In
                    </button>
                    <button type="button" id="modal-zoom-out" class="crop-btn" style="background: ${bgColor}; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">
                        🔍- Zoom Out
                    </button>
                    <button type="button" id="modal-rotate-left" class="crop-btn" style="background: ${bgColor}; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">
                        ↺ Rotate Left
                    </button>
                    <button type="button" id="modal-rotate-right" class="crop-btn" style="background: ${bgColor}; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">
                        ↻ Rotate Right
                    </button>
                    <button type="button" id="modal-reset" class="crop-btn" style="background: #757575; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold;">
                        🔄 Reset
                    </button>
                </div>

                <!-- Crop Info -->
                <div id="modal-crop-info" style="padding: 15px; background: ${fieldType === 'desktop' ? '#e3f2fd' : '#fff3e0'}; border-radius: 4px; margin-bottom: 20px; font-family: monospace; text-align: center;">
                    <strong>Crop Area:</strong> <span id="modal-crop-dimensions">Adjusting...</span>
                </div>

                <!-- Action Buttons -->
                <div style="display: flex; gap: 15px; justify-content: center;">
                    <button type="button" id="modal-cancel-btn" class="crop-btn" style="background: #6c757d; color: white; border: none; padding: 15px 40px; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold;">
                        Cancel
                    </button>
                    <button type="button" id="modal-skip-crop" class="crop-btn" style="background: #ffc107; color: black; border: none; padding: 15px 40px; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold;">
                        Skip Crop & Upload Original
                    </button>
                    <button type="button" id="modal-apply-crop" class="crop-btn" style="background: #4CAF50; color: white; border: none; padding: 15px 40px; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold;">
                        ✓ Apply Crop & Use Image
                    </button>
                </div>

                <p style="text-align: center; margin: 15px 0 0 0; color: #666; font-size: 14px;">
                    Crop the image to ${targetDims.width}x${targetDims.height}px or skip to upload original
                </p>
            </div>
        `;

        document.body.appendChild(modal);
        return modal;
    }

    // Show modal with image
    function showCropperModal(file, fieldType) {
        let modal = document.getElementById('banner-crop-modal');
        
        // Remove existing modal if any
        if (modal) {
            modal.remove();
        }
        
        currentFieldType = fieldType;
        modal = createCropperModal(fieldType);
        setupModalControls(modal, fieldType);

        const reader = new FileReader();
        reader.onload = function(e) {
            const modalImage = document.getElementById('modal-crop-image');
            modalImage.src = e.target.result;
            
            // Destroy existing cropper if any
            if (cropper) {
                cropper.destroy();
            }

            const targetRatio = aspectRatios[fieldType];

            // Initialize cropper
            cropper = new Cropper(modalImage, {
                aspectRatio: targetRatio,
                viewMode: 1,
                dragMode: 'move',
                autoCropArea: 1,
                restore: false,
                guides: true,
                center: true,
                highlight: true,
                cropBoxMovable: true,
                cropBoxResizable: true,
                toggleDragModeOnDblclick: false,
                responsive: true,
                background: true,
                modal: true,
                minCropBoxWidth: 200,
                minCropBoxHeight: 200 / targetRatio,
                crop: function(event) {
                    updateModalCropInfo(event.detail, targetRatio);
                }
            });

            modal.style.display = 'block';
        };

        reader.readAsDataURL(file);
    }

    // Update crop info in modal
    function updateModalCropInfo(detail, targetRatio) {
        const cropInfoElement = document.getElementById('modal-crop-dimensions');
        if (cropInfoElement) {
            const width = Math.round(detail.width);
            const height = Math.round(detail.height);
            const ratio = (width / height).toFixed(4);
            
            cropInfoElement.innerHTML = `
                <strong>Width:</strong> ${width}px | 
                <strong>Height:</strong> ${height}px | 
                <strong>Ratio:</strong> ${ratio}:1
                ${Math.abs(parseFloat(ratio) - targetRatio) < 0.01 ? ' ✓ Perfect!' : ''}
            `;
        }
    }

    // Setup modal controls
    function setupModalControls(modal, fieldType) {
        // Close buttons
        const closeBtn = modal.querySelector('#modal-close-btn');
        const cancelBtn = modal.querySelector('#modal-cancel-btn');
        
        const closeModal = function() {
            modal.style.display = 'none';
            if (cropper) {
                cropper.destroy();
                cropper = null;
            }
            // Reset the file input
            const imageField = document.querySelector(`input[name="${fieldType === 'desktop' ? 'image' : 'mobile_image'}"]`);
            if (imageField) {
                imageField.value = '';
            }
        };

        if (closeBtn) closeBtn.addEventListener('click', closeModal);
        if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

        // Zoom controls
        const zoomInBtn = modal.querySelector('#modal-zoom-in');
        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', function() {
                if (cropper) cropper.zoom(0.1);
            });
        }

        const zoomOutBtn = modal.querySelector('#modal-zoom-out');
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', function() {
                if (cropper) cropper.zoom(-0.1);
            });
        }

        // Rotate controls
        const rotateLeftBtn = modal.querySelector('#modal-rotate-left');
        if (rotateLeftBtn) {
            rotateLeftBtn.addEventListener('click', function() {
                if (cropper) cropper.rotate(-45);
            });
        }

        const rotateRightBtn = modal.querySelector('#modal-rotate-right');
        if (rotateRightBtn) {
            rotateRightBtn.addEventListener('click', function() {
                if (cropper) cropper.rotate(45);
            });
        }

        // Reset
        const resetBtn = modal.querySelector('#modal-reset');
        if (resetBtn) {
            resetBtn.addEventListener('click', function() {
                if (cropper) cropper.reset();
            });
        }

        // Skip crop - upload original
        const skipBtn = modal.querySelector('#modal-skip-crop');
        if (skipBtn) {
            skipBtn.addEventListener('click', function() {
                skipCropAndUploadOriginal(fieldType);
            });
        }

        // Apply crop
        const applyBtn = modal.querySelector('#modal-apply-crop');
        if (applyBtn) {
            applyBtn.addEventListener('click', function() {
                applyCroppedImage(fieldType);
            });
        }

        // Close on background click
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });

        // Close on ESC key
        const escapeHandler = function(e) {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
    }

    // Skip crop and upload original image
    function skipCropAndUploadOriginal(fieldType) {
        // Close modal
        const modal = document.getElementById('banner-crop-modal');
        if (modal) {
            modal.style.display = 'none';
        }

        // Destroy cropper
        if (cropper) {
            cropper.destroy();
            cropper = null;
        }

        // The original file is already in the input field from the change event
        // Just show success message
        showSuccessNotification('✓ Original image selected! Click "Save" button to upload.');
    }

    // Apply cropped image
    function applyCroppedImage(fieldType) {
        if (!cropper) {
            alert('Cropper not initialized');
            return;
        }

        const targetDims = dimensions[fieldType];
        const applyBtn = document.querySelector('#modal-apply-crop');
        const originalText = applyBtn.innerHTML;
        applyBtn.innerHTML = '⏳ Processing...';
        applyBtn.disabled = true;

        try {
            // Get cropped canvas
            const canvas = cropper.getCroppedCanvas({
                width: targetDims.width,
                height: targetDims.height,
                imageSmoothingEnabled: true,
                imageSmoothingQuality: 'high',
            });

            if (!canvas) {
                throw new Error('Failed to generate cropped image');
            }

            // Convert to blob
            canvas.toBlob(function(blob) {
                if (!blob) {
                    alert('Failed to create image blob');
                    applyBtn.innerHTML = originalText;
                    applyBtn.disabled = false;
                    return;
                }

                // Create File object from blob
                const timestamp = new Date().getTime();
                const filename = fieldType === 'desktop' 
                    ? `banner-cropped-${timestamp}.jpg` 
                    : `banner-mobile-cropped-${timestamp}.jpg`;
                const file = new File([blob], filename, {
                    type: 'image/jpeg',
                    lastModified: timestamp
                });

                // Update the file input
                const fieldName = fieldType === 'desktop' ? 'image' : 'mobile_image';
                const imageField = document.querySelector(`input[name="${fieldName}"]`);
                if (imageField) {
                    // Create a new FileList
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    imageField.files = dataTransfer.files;

                    // Trigger change event
                    const event = new Event('change', { bubbles: true });
                    imageField.dispatchEvent(event);
                }

                // Close modal
                const modal = document.getElementById('banner-crop-modal');
                if (modal) {
                    modal.style.display = 'none';
                }

                // Destroy cropper
                if (cropper) {
                    cropper.destroy();
                    cropper = null;
                }

                // Show success message
                const imgType = fieldType === 'desktop' ? 'Desktop' : 'Mobile';
                showSuccessNotification(`✓ ${imgType} image cropped and ready to save! Click "Save" button to upload.`);

            }, 'image/jpeg', 0.95);

        } catch (error) {
            console.error('Crop error:', error);
            alert('Error cropping image: ' + error.message);
            applyBtn.innerHTML = originalText;
            applyBtn.disabled = false;
        }
    }

    // Show success notification
    function showSuccessNotification(message) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #4CAF50;
            color: white;
            padding: 20px 30px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 1000000;
            font-size: 16px;
            font-weight: bold;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(function() {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(function() {
                notification.remove();
            }, 300);
        }, 4000);
    }

    // Setup image field watchers
    function setupImageFieldWatchers() {
        // Desktop image field
        const imageField = document.querySelector('input[name="image"]');
        if (imageField) {
            // Store original file change handler
            let originalFile = null;
            
            imageField.addEventListener('change', function(e) {
                const files = e.target.files;
                if (files && files.length > 0) {
                    originalFile = files[0];
                    currentFile = files[0];
                    
                    // Check if it's an image
                    if (!currentFile.type.match('image.*')) {
                        alert('Please select an image file');
                        e.target.value = '';
                        return;
                    }

                    // Store the original file for potential skip
                    imageField.dataset.originalFile = 'stored';
                    
                    // Show cropper modal
                    showCropperModal(currentFile, 'desktop');
                }
            });
        }

        // Mobile image field
        const mobileImageField = document.querySelector('input[name="mobile_image"]');
        if (mobileImageField) {
            // Store original file change handler
            let originalMobileFile = null;
            
            mobileImageField.addEventListener('change', function(e) {
                const files = e.target.files;
                if (files && files.length > 0) {
                    originalMobileFile = files[0];
                    currentFile = files[0];
                    
                    // Check if it's an image
                    if (!currentFile.type.match('image.*')) {
                        alert('Please select an image file');
                        e.target.value = '';
                        return;
                    }

                    // Store the original file for potential skip
                    mobileImageField.dataset.originalFile = 'stored';
                    
                    // Show cropper modal
                    showCropperModal(currentFile, 'mobile');
                }
            });
        }
    }

    // Setup existing image croppers (for already uploaded images)
    function setupExistingImageCroppers() {
        // Desktop image cropper
        setupExistingCropper('desktop', 'banner-image-to-crop', 'crop', aspectRatios.desktop, dimensions.desktop);
        
        // Mobile image cropper
        setupExistingCropper('mobile', 'banner-mobile-image-to-crop', 'mobile-crop', aspectRatios.mobile, dimensions.mobile);
    }

    function setupExistingCropper(type, imageElementId, controlPrefix, targetRatio, targetDims) {
        const imageElement = document.getElementById(imageElementId);
        if (!imageElement) return;

        let existingCropper = null;

        function createExistingCropper() {
            if (existingCropper) {
                existingCropper.destroy();
            }

            existingCropper = new Cropper(imageElement, {
                aspectRatio: targetRatio,
                viewMode: 1,
                dragMode: 'move',
                autoCropArea: 1,
                restore: false,
                guides: true,
                center: true,
                highlight: true,
                cropBoxMovable: true,
                cropBoxResizable: true,
                toggleDragModeOnDblclick: false,
                responsive: true,
                background: true,
                modal: true,
                minCropBoxWidth: 200,
                minCropBoxHeight: 200 / targetRatio,
                crop: function(event) {
                    updateExistingCropInfo(event.detail, controlPrefix, targetRatio);
                }
            });
        }

        function updateExistingCropInfo(detail, prefix, ratio) {
            const cropInfoElement = document.getElementById(`${prefix}-dimensions`);
            if (cropInfoElement) {
                const width = Math.round(detail.width);
                const height = Math.round(detail.height);
                const currentRatio = (width / height).toFixed(4);
                
                cropInfoElement.innerHTML = `
                    <strong>Width:</strong> ${width}px | 
                    <strong>Height:</strong> ${height}px | 
                    <strong>Ratio:</strong> ${currentRatio}:1
                `;
            }
        }

        createExistingCropper();

        // Setup controls for existing image cropper
        const zoomInBtn = document.getElementById(`${controlPrefix}-zoom-in`);
        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', function(e) {
                e.preventDefault();
                if (existingCropper) existingCropper.zoom(0.1);
            });
        }

        const zoomOutBtn = document.getElementById(`${controlPrefix}-zoom-out`);
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', function(e) {
                e.preventDefault();
                if (existingCropper) existingCropper.zoom(-0.1);
            });
        }

        const rotateLeftBtn = document.getElementById(`${controlPrefix}-rotate-left`);
        if (rotateLeftBtn) {
            rotateLeftBtn.addEventListener('click', function(e) {
                e.preventDefault();
                if (existingCropper) existingCropper.rotate(-45);
            });
        }

        const rotateRightBtn = document.getElementById(`${controlPrefix}-rotate-right`);
        if (rotateRightBtn) {
            rotateRightBtn.addEventListener('click', function(e) {
                e.preventDefault();
                if (existingCropper) existingCropper.rotate(45);
            });
        }

        const resetBtn = document.getElementById(`${controlPrefix}-reset`);
        if (resetBtn) {
            resetBtn.addEventListener('click', function(e) {
                e.preventDefault();
                if (existingCropper) existingCropper.reset();
            });
        }

        const downloadBtn = document.getElementById(`${controlPrefix}-download`);
        if (downloadBtn) {
            downloadBtn.addEventListener('click', function(e) {
                e.preventDefault();
                downloadExistingCrop(existingCropper, type, targetDims);
            });
        }
    }

    // Download cropped version of existing image
    function downloadExistingCrop(cropperInstance, type, targetDims) {
        if (!cropperInstance) {
            alert('Cropper not initialized');
            return;
        }

        const downloadBtn = document.getElementById(`${type === 'desktop' ? 'crop' : 'mobile-crop'}-download`);
        const originalText = downloadBtn.innerHTML;
        downloadBtn.innerHTML = '⏳ Processing...';
        downloadBtn.disabled = true;

        try {
            const canvas = cropperInstance.getCroppedCanvas({
                width: targetDims.width,
                height: targetDims.height,
                imageSmoothingEnabled: true,
                imageSmoothingQuality: 'high',
            });

            if (!canvas) {
                throw new Error('Failed to generate cropped image');
            }

            canvas.toBlob(function(blob) {
                if (!blob) {
                    alert('Failed to create image blob');
                    downloadBtn.innerHTML = originalText;
                    downloadBtn.disabled = false;
                    return;
                }

                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                const timestamp = new Date().getTime();
                const filename = type === 'desktop' 
                    ? `banner-cropped-${targetDims.width}x${targetDims.height}-${timestamp}.jpg`
                    : `banner-mobile-cropped-${targetDims.width}x${targetDims.height}-${timestamp}.jpg`;
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);

                downloadBtn.innerHTML = '✓ Downloaded!';
                downloadBtn.disabled = false;

                const imgType = type === 'desktop' ? 'Desktop' : 'Mobile';
                showSuccessNotification(`✓ ${imgType} image downloaded! Re-upload it in the "${imgType === 'Desktop' ? 'Image' : 'Mobile Image'}" field above.`);

                setTimeout(function() {
                    downloadBtn.innerHTML = originalText;
                }, 3000);
            }, 'image/jpeg', 0.95);

        } catch (error) {
            console.error('Crop error:', error);
            alert('Error cropping image: ' + error.message);
            downloadBtn.innerHTML = originalText;
            downloadBtn.disabled = false;
        }
    }

    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }

        .crop-btn {
            transition: all 0.2s ease;
        }

        .crop-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            opacity: 0.9;
        }

        .crop-btn:active {
            transform: translateY(0);
        }
    `;
    document.head.appendChild(style);

})();

