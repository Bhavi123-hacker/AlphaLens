import { afterEach, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SaveResearchCandidate } from '../src/components/SaveResearchCandidate'

// TEST_ONLY personal records, never real user writes or provider data.
const state = vi.hoisted(() => ({ editable: true, keys: ['TEST_ONLY_ORIGINAL'], post: vi.fn() }))
vi.mock('../src/api/personal-hooks', () => ({ usePersonal: () => ({ data: { data: { mutations_enabled: state.editable, watchlists: [{ id: 'TEST_ONLY_LIST', revision: 7, value: { name: 'TEST_ONLY research', instrument_keys: state.keys } }] } }, isPending: false, isError: false }) }))
vi.mock('../src/api/client', () => ({ personalPost: (...args: unknown[]) => state.post(...args) }))
function mount() { render(<MemoryRouter><QueryClientProvider client={new QueryClient()}><SaveResearchCandidate instrumentKey="TEST_ONLY_NEW" /></QueryClientProvider></MemoryRouter>) }
afterEach(() => { state.editable = true; state.keys = ['TEST_ONLY_ORIGINAL']; state.post.mockReset() })

it('saves only the selected identity with the current owned revision and preserves existing keys', async () => {
  state.post.mockResolvedValue({ data: {} })
  mount()
  expect(state.post).not.toHaveBeenCalled()
  await userEvent.click(screen.getByText('Save to a watchlist'))
  await userEvent.click(await screen.findByRole('button', { name: 'Save security identity' }))
  await waitFor(() => expect(state.post).toHaveBeenCalledTimes(1))
  expect(state.post.mock.calls[0][2]).toEqual({ id: 'TEST_ONLY_LIST', revision: 7, value: { name: 'TEST_ONLY research', instrument_keys: ['TEST_ONLY_ORIGINAL', 'TEST_ONLY_NEW'] } })
  expect(await screen.findByRole('status')).toHaveTextContent('Security saved privately')
})

it.each(['duplicate', 'full', 'readonly'])('refuses an unsafe %s watchlist write', async reason => {
  if (reason === 'duplicate') state.keys = ['TEST_ONLY_NEW']
  if (reason === 'full') state.keys = Array.from({ length: 50 }, (_, i) => `TEST_ONLY_${i}`)
  if (reason === 'readonly') state.editable = false
  mount()
  await userEvent.click(screen.getByText('Save to a watchlist'))
  expect(await screen.findByRole('button')).toBeDisabled()
  expect(state.post).not.toHaveBeenCalled()
})
