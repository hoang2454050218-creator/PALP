import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { useToast, toast } from '../use-toast'

beforeEach(() => {
  useToast.setState({ toasts: [] })
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useToast', () => {
  it('starts with empty toasts array', () => {
    expect(useToast.getState().toasts).toEqual([])
  })

  describe('add', () => {
    it('adds a toast with generated id', () => {
      useToast.getState().add({
        variant: 'success',
        title: 'Saved!',
      })

      const { toasts } = useToast.getState()
      expect(toasts).toHaveLength(1)
      expect(toasts[0].variant).toBe('success')
      expect(toasts[0].title).toBe('Saved!')
      expect(toasts[0].id).toBeTruthy()
    })

    it('adds multiple toasts', () => {
      useToast.getState().add({ variant: 'success', title: 'First' })
      useToast.getState().add({ variant: 'error', title: 'Second' })

      expect(useToast.getState().toasts).toHaveLength(2)
    })

    it('auto-dismisses toast after default duration', () => {
      useToast.getState().add({ variant: 'info', title: 'Temporary' })
      expect(useToast.getState().toasts).toHaveLength(1)

      vi.advanceTimersByTime(5000)
      expect(useToast.getState().toasts).toHaveLength(0)
    })

    it('respects custom duration', () => {
      useToast.getState().add({
        variant: 'warning',
        title: 'Custom',
        duration: 2000,
      })

      vi.advanceTimersByTime(1999)
      expect(useToast.getState().toasts).toHaveLength(1)

      vi.advanceTimersByTime(2)
      expect(useToast.getState().toasts).toHaveLength(0)
    })

    it('does not auto-dismiss when duration is 0', () => {
      useToast.getState().add({
        variant: 'error',
        title: 'Persistent',
        duration: 0,
      })

      vi.advanceTimersByTime(60000)
      expect(useToast.getState().toasts).toHaveLength(1)
    })

    it('supports description', () => {
      useToast.getState().add({
        variant: 'success',
        title: 'Done',
        description: 'Task completed successfully',
      })

      expect(useToast.getState().toasts[0].description).toBe(
        'Task completed successfully',
      )
    })

    it('supports action', () => {
      const onClick = vi.fn()
      useToast.getState().add({
        variant: 'info',
        title: 'Undo?',
        action: { label: 'Undo', onClick },
      })

      const action = useToast.getState().toasts[0].action
      expect(action?.label).toBe('Undo')
      action?.onClick()
      expect(onClick).toHaveBeenCalled()
    })
  })

  describe('dismiss', () => {
    it('removes toast by id', () => {
      useToast.getState().add({
        variant: 'success',
        title: 'Keep',
        duration: 0,
      })
      useToast.getState().add({
        variant: 'error',
        title: 'Remove',
        duration: 0,
      })

      const toRemove = useToast.getState().toasts[1]
      useToast.getState().dismiss(toRemove.id)

      const { toasts } = useToast.getState()
      expect(toasts).toHaveLength(1)
      expect(toasts[0].title).toBe('Keep')
    })

    it('does nothing for non-existent id', () => {
      useToast.getState().add({
        variant: 'info',
        title: 'Stays',
        duration: 0,
      })

      useToast.getState().dismiss('non-existent')
      expect(useToast.getState().toasts).toHaveLength(1)
    })
  })
})

describe('toast helper function', () => {
  it('adds a toast via the convenience function', () => {
    toast({ variant: 'success', title: 'Quick toast' })
    expect(useToast.getState().toasts).toHaveLength(1)
    expect(useToast.getState().toasts[0].title).toBe('Quick toast')
  })
})
