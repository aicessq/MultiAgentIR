import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType } from 'docx'
import html2pdf from 'html2pdf.js'

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// --- Markdown Export ---

export function exportMarkdown(report: any, filename = 'report.md') {
  const lines: string[] = []
  if (report.title) lines.push(`# ${report.title}\n`)
  if (report.as_of_date) lines.push(`> As of: ${report.as_of_date}\n`)

  const summary = typeof report.executive_summary === 'string'
    ? report.executive_summary
    : report.executive_summary?.content || ''
  if (summary) lines.push(`> ${summary}\n`)

  for (const section of report.sections || []) {
    lines.push(`## ${section.heading}\n`)
    lines.push(`${section.content}\n`)

    if (section.key_claims?.length) {
      lines.push('**Key Claims:**')
      for (const kc of section.key_claims) {
        lines.push(`- [${kc.confidence}] ${kc.claim_id}: ${kc.sentence}`)
      }
      lines.push('')
    }

    if (section.claim_ids?.length && !section.key_claims?.length) {
      lines.push(`**Claim IDs:** ${section.claim_ids.join(', ')}\n`)
    }

    if (section.citations?.length) {
      lines.push('**Citations:**')
      for (const url of section.citations) lines.push(`- ${url}`)
      lines.push('')
    }

    if (section.uncertainties?.length) {
      lines.push('**Uncertainties:**')
      for (const u of section.uncertainties) lines.push(`- ${u}`)
      lines.push('')
    }
  }

  if (report.risk_register?.length) {
    lines.push('## Risk Register\n')
    for (const risk of report.risk_register) {
      lines.push(`### ${risk.risk}`)
      lines.push(`- Likelihood: ${risk.likelihood}, Impact: ${risk.impact}`)
      if (risk.mechanism) lines.push(`- Mechanism: ${risk.mechanism}`)
      if (risk.evidence_claim_ids?.length) lines.push(`- Evidence: ${risk.evidence_claim_ids.join(', ')}`)
      if (risk.monitoring_indicators?.length) lines.push(`- Monitoring: ${risk.monitoring_indicators.join(', ')}`)
      lines.push('')
    }
  }

  if (report.limitations?.length) {
    lines.push('## Limitations\n')
    for (const l of report.limitations) lines.push(`- ${l}`)
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' })
  downloadBlob(blob, filename)
}

// --- PDF Export ---

export function exportPdf(report: any, filename = 'report.pdf') {
  const container = document.createElement('div')
  container.style.fontFamily = 'system-ui, -apple-system, sans-serif'
  container.style.color = '#1a1a1a'
  container.style.padding = '40px'
  container.style.maxWidth = '800px'

  let html = ''
  if (report.title) html += `<h1 style="font-size:24px;margin-bottom:8px;">${report.title}</h1>`
  if (report.as_of_date) html += `<div style="font-size:11px;color:#888;margin-bottom:16px;">As of: ${report.as_of_date}</div>`

  const summary = typeof report.executive_summary === 'string'
    ? report.executive_summary
    : report.executive_summary?.content || ''
  if (summary) html += `<blockquote style="border-left:3px solid #00f0ff;padding-left:12px;color:#555;margin-bottom:24px;">${summary}</blockquote>`

  for (const section of report.sections || []) {
    html += `<h2 style="font-size:18px;margin-top:24px;margin-bottom:8px;color:#333;">${section.heading}</h2>`
    html += `<div style="line-height:1.7;color:#444;white-space:pre-wrap;">${section.content}</div>`

    if (section.key_claims?.length) {
      html += '<div style="margin-top:8px;font-size:11px;color:#666;">'
      html += '<strong>Key Claims:</strong><br/>'
      for (const kc of section.key_claims) {
        html += `<span style="color:#7c3aed;">[${kc.confidence}]</span> ${kc.claim_id}: ${kc.sentence}<br/>`
      }
      html += '</div>'
    }

    if (section.claim_ids?.length && !section.key_claims?.length) {
      html += `<div style="margin-top:4px;font-size:10px;color:#7c3aed;">Claim IDs: ${section.claim_ids.join(', ')}</div>`
    }

    if (section.citations?.length) {
      html += '<div style="margin-top:8px;font-size:11px;color:#888;">Citations: '
      html += section.citations.join(' | ')
      html += '</div>'
    }
  }

  if (report.risk_register?.length) {
    html += '<h2 style="font-size:16px;margin-top:24px;color:#e65100;">Risk Register</h2>'
    for (const risk of report.risk_register) {
      html += `<div style="margin-bottom:12px;padding:8px;border:1px solid #fde68a;border-radius:4px;">`
      html += `<strong>${risk.risk}</strong> <span style="color:#888;font-size:11px;">(${risk.likelihood}/${risk.impact})</span><br/>`
      if (risk.mechanism) html += `<span style="font-size:12px;color:#555;">${risk.mechanism}</span><br/>`
      if (risk.evidence_claim_ids?.length) html += `<span style="font-size:10px;color:#888;">Evidence: ${risk.evidence_claim_ids.join(', ')}</span>`
      html += '</div>'
    }
  }

  if (report.limitations?.length) {
    html += '<h2 style="font-size:16px;margin-top:24px;color:#e65100;">Limitations</h2><ul>'
    for (const l of report.limitations) html += `<li style="color:#666;margin-bottom:4px;">${l}</li>`
    html += '</ul>'
  }
  container.innerHTML = html

  html2pdf().set({
    margin: 10,
    filename,
    html2canvas: { scale: 2 },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
  }).from(container).save()
}

// --- Word Export ---

export function exportWord(report: any, filename = 'report.docx') {
  const children: Paragraph[] = []

  if (report.title) {
    children.push(new Paragraph({
      heading: HeadingLevel.HEADING_1,
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: report.title, bold: true, size: 32 })],
    }))
  }

  if (report.as_of_date) {
    children.push(new Paragraph({
      children: [new TextRun({ text: `As of: ${report.as_of_date}`, size: 18, color: '888888' })],
      spacing: { after: 200 },
    }))
  }

  const summary = typeof report.executive_summary === 'string'
    ? report.executive_summary
    : report.executive_summary?.content || ''
  if (summary) {
    children.push(new Paragraph({
      children: [new TextRun({ text: summary, italics: true, size: 22, color: '555555' })],
      spacing: { after: 300 },
    }))
  }

  for (const section of report.sections || []) {
    children.push(new Paragraph({
      heading: HeadingLevel.HEADING_2,
      children: [new TextRun({ text: section.heading, bold: true, size: 26 })],
      spacing: { before: 300 },
    }))
    children.push(new Paragraph({
      children: [new TextRun({ text: section.content, size: 22 })],
      spacing: { after: 200 },
    }))

    if (section.key_claims?.length) {
      children.push(new Paragraph({
        children: [new TextRun({ text: 'Key Claims:', bold: true, size: 20 })],
        spacing: { before: 100 },
      }))
      for (const kc of section.key_claims) {
        children.push(new Paragraph({
          children: [new TextRun({ text: `[${kc.confidence}] ${kc.claim_id}: ${kc.sentence}`, size: 20 })],
          spacing: { after: 50 },
        }))
      }
    }

    if (section.claim_ids?.length && !section.key_claims?.length) {
      children.push(new Paragraph({
        children: [new TextRun({ text: 'Claim IDs: ' + section.claim_ids.join(', '), size: 18, color: '7c3aed' })],
        spacing: { after: 100 },
      }))
    }

    if (section.citations?.length) {
      children.push(new Paragraph({
        children: [new TextRun({ text: 'Citations: ' + section.citations.join(' | '), size: 18, color: '888888' })],
        spacing: { after: 200 },
      }))
    }
  }

  if (report.risk_register?.length) {
    children.push(new Paragraph({
      heading: HeadingLevel.HEADING_2,
      children: [new TextRun({ text: 'Risk Register', bold: true, size: 26, color: 'E65100' })],
      spacing: { before: 300 },
    }))
    for (const risk of report.risk_register) {
      children.push(new Paragraph({
        children: [
          new TextRun({ text: risk.risk, bold: true, size: 22 }),
          new TextRun({ text: ` (${risk.likelihood}/${risk.impact})`, size: 20, color: '888888' }),
        ],
        spacing: { before: 100 },
      }))
      if (risk.mechanism) {
        children.push(new Paragraph({
          children: [new TextRun({ text: risk.mechanism, size: 20, color: '555555' })],
        }))
      }
    }
  }

  if (report.limitations?.length) {
    children.push(new Paragraph({
      heading: HeadingLevel.HEADING_2,
      children: [new TextRun({ text: 'Limitations', bold: true, size: 26, color: 'E65100' })],
      spacing: { before: 300 },
    }))
    for (const l of report.limitations) {
      children.push(new Paragraph({
        children: [new TextRun({ text: `• ${l}`, size: 22 })],
      }))
    }
  }

  const doc = new Document({ sections: [{ children }] })
  Packer.toBlob(doc).then(blob => downloadBlob(blob, filename))
}
