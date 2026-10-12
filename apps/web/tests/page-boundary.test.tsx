import { expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PageBoundary } from '../src/components/PageBoundary'

it('page failures provide a recovery action without exposing raw exception details', () => {
  const log = vi.spyOn(console, 'error').mockImplementation(() => {})
  function Broken(): never { throw new Error('TEST_ONLY_PRIVATE_EXCEPTION_DETAIL') }
  try {
    render(<PageBoundary><Broken /></PageBoundary>)
    expect(screen.getByRole('alert')).toHaveTextContent('Page could not be loaded')
    expect(screen.getByRole('button', { name: 'Reload local page' })).toBeInTheDocument()
    expect(screen.queryByText('TEST_ONLY_PRIVATE_EXCEPTION_DETAIL')).not.toBeInTheDocument()
  } finally { log.mockRestore() }
})
