/**
 * PDF Export Utility
 * Exports dashboard views to PDF with white-labeling support
 */

interface ExportOptions {
  title?: string;
  logoUrl?: string;
  includeDate?: boolean;
  includeCharts?: boolean;
}

export async function exportToPDF(
  elementId: string,
  filename: string = 'dashboard-export.pdf',
  options: ExportOptions = {}
): Promise<void> {
  try {
    // Dynamic import of html2pdf library
    const html2pdf = (await import('html2pdf.js')).default;
    
    const element = document.getElementById(elementId);
    if (!element) {
      throw new Error(`Element with id "${elementId}" not found`);
    }

    // Create a clone for export (to avoid affecting the original)
    const clone = element.cloneNode(true) as HTMLElement;
    
    // Add logo and header if provided
    if (options.logoUrl || options.title) {
      const header = document.createElement('div');
      header.style.padding = '20px';
      header.style.borderBottom = '2px solid #e5e7eb';
      header.style.marginBottom = '20px';
      
      if (options.logoUrl) {
        const logo = document.createElement('img');
        logo.src = options.logoUrl;
        logo.style.height = '40px';
        logo.style.marginBottom = '10px';
        header.appendChild(logo);
      }
      
      if (options.title) {
        const title = document.createElement('h1');
        title.textContent = options.title;
        title.style.fontSize = '24px';
        title.style.fontWeight = 'bold';
        title.style.margin = '0';
        header.appendChild(title);
      }
      
      if (options.includeDate) {
        const date = document.createElement('p');
        date.textContent = `Generated: ${new Date().toLocaleString()}`;
        date.style.fontSize = '12px';
        date.style.color = '#6b7280';
        date.style.marginTop = '5px';
        header.appendChild(date);
      }
      
      clone.insertBefore(header, clone.firstChild);
    }

    // Configure PDF options
    const opt = {
      margin: [10, 10, 10, 10] as [number, number, number, number],
      filename: filename,
      image: { type: 'jpeg' as const, quality: 0.98 },
      html2canvas: {
        scale: 2,
        useCORS: true,
        logging: false,
      },
      jsPDF: {
        unit: 'mm' as const,
        format: 'a4' as const,
        orientation: 'portrait' as const,
      },
    };

    // Generate and download PDF
    await html2pdf().set(opt).from(clone).save();
  } catch (error) {
    console.error('PDF export failed:', error);
    throw error;
  }
}

/**
 * Export table data to PDF
 */
export async function exportTableToPDF(
  tableId: string,
  title: string,
  filename: string = 'table-export.pdf',
  logoUrl?: string
): Promise<void> {
  return exportToPDF(tableId, filename, {
    title,
    logoUrl,
    includeDate: true,
  });
}

/**
 * Export dashboard view to PDF
 */
export async function exportDashboardToPDF(
  dashboardId: string = 'dashboard-content',
  filename: string = 'dashboard-export.pdf',
  logoUrl?: string
): Promise<void> {
  return exportToPDF(dashboardId, filename, {
    title: 'Amazon PPC AI Dashboard Report',
    logoUrl,
    includeDate: true,
    includeCharts: true,
  });
}

