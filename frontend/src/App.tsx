import React, { useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import * as echarts from 'echarts'

export type Part = { type: 'markdown'; content: string } | { type: 'html'; html: string }

type ToolEvent = {
	type: 'tool'
	name: string
	status: 'running' | 'success' | 'error'
	data: any
}

type TokenEvent = { type: 'token'; text: string }

type DoneEvent = { type: 'done' }

type ChatEvent = ToolEvent | TokenEvent | DoneEvent

function generateToolContainerHtml(tool: ToolEvent, index: number): string {
	const id = `tool-container-${index}`
	return `<div class="tool-card" data-tool="${tool.name}" data-status="${tool.status}"><div id="${id}"></div></div>`
}

function renderToolIntoContainer(tool: ToolEvent, container: HTMLElement) {
	if (tool.name === 'db_query' && tool.status === 'success') {
		const chartSpec = tool.data?.chart
		if (chartSpec?.type === 'echarts' && chartSpec.option) {
			const chart = echarts.init(container)
			chart.setOption(chartSpec.option)
			return
		}
		container.innerText = JSON.stringify(tool.data, null, 2)
		return
	}
	if (tool.name === 'html_validate' && tool.status === 'success') {
		container.innerText = JSON.stringify(tool.data, null, 2)
		return
	}
	if (tool.status === 'running') {
		container.innerText = '工具执行中…'
		return
	}
	container.innerText = '未匹配的工具输出'
}

export const App: React.FC = () => {
	const [input, setInput] = useState('给我各类销售额Top5的报表，并用柱状图展示')
	const [parts, setParts] = useState<Part[]>([])
	const toolIndexRef = useRef(0)
	const toolMountQueue = useRef<{ index: number; tool: ToolEvent }[]>([])
	const containerRef = useRef<HTMLDivElement>(null)

	function reset() {
		setParts([])
		toolIndexRef.current = 0
		toolMountQueue.current = []
	}

	function appendMarkdown(text: string) {
		setParts(prev => {
			const last = prev[prev.length - 1]
			if (last && last.type === 'markdown') {
				return [...prev.slice(0, -1), { type: 'markdown', content: last.content + text }]
			}
			return [...prev, { type: 'markdown', content: text }]
		})
	}

	function appendTool(tool: ToolEvent) {
		const index = toolIndexRef.current++
		const html = generateToolContainerHtml(tool, index)
		setParts(prev => [...prev, { type: 'html', html }])
		toolMountQueue.current.push({ index, tool })
	}

	function updateRunningTool(tool: ToolEvent) {
		// For simplicity, append a new container for updates
		appendTool(tool)
	}

	function handleEvent(ev: ChatEvent) {
		if (ev.type === 'token') {
			appendMarkdown(ev.text)
			return
		}
		if (ev.type === 'tool') {
			if (ev.status === 'running') appendTool(ev)
			else updateRunningTool(ev)
			return
		}
		if (ev.type === 'done') {
			// no-op
		}
	}

	function mountTools() {
		if (!containerRef.current) return
		const rootEl = containerRef.current
		for (const item of toolMountQueue.current) {
			const container = rootEl.querySelector<HTMLDivElement>(`#tool-container-${item.index}`)
			if (container) {
				renderToolIntoContainer(item.tool, container)
			}
		}
		toolMountQueue.current = []
	}

	React.useEffect(() => {
		mountTools()
	})

	async function send() {
		reset()
		const resp = await fetch('http://localhost:8000/chat', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
			body: JSON.stringify({ content: input })
		})
		if (!resp.body) return
		const reader = resp.body.getReader()
		const decoder = new TextDecoder('utf-8')
		let buffer = ''
		while (true) {
			const { value, done } = await reader.read()
			if (done) break
			buffer += decoder.decode(value, { stream: true })
			let idx
			while ((idx = buffer.indexOf('\n\n')) !== -1) {
				const chunk = buffer.slice(0, idx)
				buffer = buffer.slice(idx + 2)
				if (chunk.startsWith('data: ')) {
					const jsonStr = chunk.slice(6)
					try {
						const evt = JSON.parse(jsonStr) as ChatEvent
						handleEvent(evt)
					} catch (e) {
						// ignore
					}
				}
			}
		}
	}

	return (
		<div style={{ maxWidth: 860, margin: '32px auto', padding: 16 }}>
			<h2>AI Chat</h2>
			<div style={{ display: 'flex', gap: 8 }}>
				<input style={{ flex: 1 }} value={input} onChange={e => setInput(e.target.value)} placeholder="输入你的问题…" />
				<button onClick={send}>发送</button>
			</div>
			<div ref={containerRef} style={{ marginTop: 16 }}>
				{parts.map((p, i) => (
					p.type === 'markdown' ? (
						<div key={i} className="md-part">
							<ReactMarkdown remarkPlugins={[remarkGfm]}>{p.content}</ReactMarkdown>
						</div>
					) : (
						<div key={i} className="html-part" dangerouslySetInnerHTML={{ __html: p.html }} />
					)
				))}
			</div>
		</div>
	)
}