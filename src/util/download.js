/** Hand `data` (bytes or text) to the browser as a file download. */
export function saveFile(data, type, fileName) {
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob([data], { type }))
  link.download = fileName
  link.click()
  setTimeout(() => URL.revokeObjectURL(link.href), 5000)
}
