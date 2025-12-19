"""
PDF Watermarking Utility for GyanAangan
Adds branded watermark to PDF resources
"""
import io
import os
from typing import BinaryIO
from datetime import datetime

try:
    from pypdf import PdfReader, PdfWriter, Transformation
    from pypdf.generic import RectangleObject
except ImportError:
    from PyPDF2 import PdfReader, PdfWriter
    from PyPDF2.generic import RectangleObject
    Transformation = None

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.colors import Color
from django.core.files.base import ContentFile


class PDFWatermarker:
    """Add watermark to PDF files"""
    
    def __init__(
        self, 
        watermark_text="Visit GyanAangan.in For More Such Content",
        opacity=0.3,
        font_name="Helvetica-Bold",
        font_size=20,
        position="both"
    ):
        """
        Initialize PDF Watermarker
        
        Args:
            watermark_text: Text to display as watermark
            opacity: Transparency (0.0 to 1.0, where 1.0 is fully opaque)
            font_name: Font to use for watermark
            font_size: Size of watermark text
            position: Position of watermark ('top', 'bottom', 'center', 'both')
        """
        self.watermark_text = watermark_text
        self.opacity = opacity
        self.font_name = font_name
        self.font_size = font_size
        self.position = position
    
    def create_watermark_page(self, page_width, page_height):
        """
        Create a watermark page using ReportLab
        
        Args:
            page_width: Width of the page
            page_height: Height of the page
            
        Returns:
            BytesIO object containing the watermark PDF
        """
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))
        
        # Set transparency
        can.setFillColor(Color(0, 0, 0, alpha=self.opacity))
        can.setFont(self.font_name, self.font_size)
        
        # Calculate text width for positioning
        text_width = can.stringWidth(self.watermark_text, self.font_name, self.font_size)
        
        # URL with UTM parameters for tracking
        tracking_url = "https://gyanaangan.in/?utm_source=pdf&utm_medium=watermark&utm_campaign=resource"
        
        # Position watermark(s) based on preference
        positions_to_draw = []
        
        if self.position == "bottom":
            positions_to_draw.append(60)  # 60 points from bottom
        elif self.position == "top":
            positions_to_draw.append(page_height - 80)  # 80 points from top
        elif self.position == "center":
            positions_to_draw.append(page_height / 2)
        elif self.position == "both":
            positions_to_draw.append(60)  # Bottom
            positions_to_draw.append(page_height - 80)  # Top
        else:
            positions_to_draw.append(60)  # Default to bottom
        
        # Draw watermark at each position
        for y_position in positions_to_draw:
            # Center horizontally
            x_position = (page_width - text_width) / 2
            
            # Draw main watermark text
            can.setFont(self.font_name, self.font_size)
            can.drawString(x_position, y_position, self.watermark_text)
            
            # Make the entire text clickable with link annotation
            # Create a rectangle around the text for the clickable area
            link_rect = (
                x_position - 5,  # Left (with small padding)
                y_position - 5,  # Bottom (with small padding)
                x_position + text_width + 5,  # Right (with small padding)
                y_position + self.font_size + 5  # Top (with small padding)
            )
            can.linkURL(tracking_url, link_rect, relative=0)
        
        can.save()
        packet.seek(0)
        return packet
    
    def add_watermark_to_pdf(self, input_pdf_path_or_file):
        """
        Add watermark to PDF file
        
        Args:
            input_pdf_path_or_file: Path to PDF file or file-like object
            
        Returns:
            BytesIO object containing watermarked PDF
        """
        # Read the input PDF
        if isinstance(input_pdf_path_or_file, str):
            with open(input_pdf_path_or_file, 'rb') as file:
                pdf_reader = PdfReader(file)
                return self._process_pdf(pdf_reader)
        else:
            # It's a file-like object
            input_pdf_path_or_file.seek(0)
            pdf_reader = PdfReader(input_pdf_path_or_file)
            return self._process_pdf(pdf_reader)
    
    def _process_pdf(self, pdf_reader):
        """
        Process PDF and add watermark to each page
        
        Args:
            pdf_reader: PdfReader object
            
        Returns:
            BytesIO object containing watermarked PDF
        """
        pdf_writer = PdfWriter()
        
        # Process each page
        for page_num, page in enumerate(pdf_reader.pages):
            # Get page dimensions
            page_box = page.mediabox
            page_width = float(page_box.width)
            page_height = float(page_box.height)
            
            # Create watermark for this page size
            watermark_pdf = self.create_watermark_page(page_width, page_height)
            watermark_reader = PdfReader(watermark_pdf)
            watermark_page = watermark_reader.pages[0]
            
            # Merge watermark with original page
            page.merge_page(watermark_page)
            pdf_writer.add_page(page)
        
        # Write to output
        output = io.BytesIO()
        pdf_writer.write(output)
        output.seek(0)
        return output
    
    def watermark_resource_file(self, resource, backup_original=True):
        """
        Watermark a Django Resource model's file field
        
        Args:
            resource: Resource model instance with file field
            backup_original: If True, saves original file to original_file field
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not resource.file:
            return False
        
        # Check if it's a PDF
        file_name = resource.file.name
        if not file_name.lower().endswith('.pdf'):
            return False
        
        try:
            # Backup original file if requested and not already backed up
            if backup_original and not resource.original_file:
                resource.file.seek(0)
                original_content = resource.file.read()
                original_filename = os.path.basename(file_name)
                
                # Save to original_file field
                resource.original_file.save(
                    original_filename,
                    ContentFile(original_content),
                    save=False
                )
                print(f"✅ Backed up original file: {original_filename}")
            
            # Get the file content for watermarking
            resource.file.seek(0)
            file_content = resource.file.read()
            
            # Create file-like object
            input_file = io.BytesIO(file_content)
            
            # Add watermark
            watermarked_pdf = self.add_watermark_to_pdf(input_file)
            
            # Generate new filename with timestamp to avoid caching issues
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = os.path.basename(file_name)
            name_without_ext = os.path.splitext(original_name)[0]
            new_filename = f"{name_without_ext}_watermarked_{timestamp}.pdf"
            
            # Save the watermarked PDF back to the resource
            resource.file.save(
                new_filename,
                ContentFile(watermarked_pdf.read()),
                save=True
            )
            
            print(f"✅ Watermarked file: {new_filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error watermarking PDF {resource.name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def add_watermark_to_resources(resources_queryset, request=None, backup_original=True):
    """
    Add watermark to multiple resources (admin action helper)
    
    Args:
        resources_queryset: QuerySet of Resource objects
        request: Django request object (optional, for messages)
        backup_original: If True, backup original files before watermarking
        
    Returns:
        dict: Statistics about the operation
    """
    watermarker = PDFWatermarker(
        watermark_text="Visit GyanAangan.in For More Such Content",
        opacity=0.3,  # 30% opacity for better visibility
        font_size=20,  # Larger font size
        position="both"  # Both top and bottom
    )
    
    stats = {
        'total': resources_queryset.count(),
        'processed': 0,
        'backed_up': 0,
        'skipped': 0,
        'failed': 0,
        'not_pdf': 0,
        'no_file': 0
    }
    
    for resource in resources_queryset:
        if not resource.file:
            stats['no_file'] += 1
            stats['skipped'] += 1
            continue
        
        file_name = resource.file.name
        if not file_name.lower().endswith('.pdf'):
            stats['not_pdf'] += 1
            stats['skipped'] += 1
            continue
        
        # Track if backup was created
        had_backup_before = bool(resource.original_file)
        
        success = watermarker.watermark_resource_file(resource, backup_original=backup_original)
        if success:
            stats['processed'] += 1
            # Check if backup was created during this operation
            if backup_original and not had_backup_before and resource.original_file:
                stats['backed_up'] += 1
        else:
            stats['failed'] += 1
    
    return stats
