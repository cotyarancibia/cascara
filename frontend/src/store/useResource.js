import { useCallback, useEffect, useState } from 'react'

export function useResource(loader) {
  const [version, setVersion] = useState(0)
  const [state, setState] = useState({ loading: true, data: null, error: null, loader })
  const reload = useCallback(() => { setState((previous) => ({ ...previous, loading: true, error: null })); setVersion((v) => v + 1) }, [])
  useEffect(() => {
    let active = true
    Promise.resolve().then(loader).then((data) => { if (active) setState({ loading: false, data, error: null, loader }) }).catch((error) => { if (active) setState({ loading: false, data: null, error, loader }) })
    return () => { active = false }
  }, [loader, version])
  return { ...state, loading: state.loading || state.loader !== loader, reload }
}
