import { useEffect, useState } from 'react'
import { get } from './api'

// Load one API path into a component. `data` is null until it arrives.
export function useGet(path) {
  const [result, setResult] = useState({ path: null, data: null, error: '' })

  useEffect(() => {
    let current = true
    get(path)
      .then((data) => current && setResult({ path, data, error: '' }))
      .catch((error) => current && setResult({ path, data: null, error: error.message }))
    return () => {
      current = false
    }
  }, [path])

  return result.path === path ? result : { data: null, error: result.error }
}
