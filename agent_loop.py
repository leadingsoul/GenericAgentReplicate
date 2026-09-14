import json, re, os
from dataclasses import dataclass
from typing import Any, Optional
try: from plugins.hooks import trigger as _hook
except ImportError: _hook = lambda *a, **k: None
# 数据类：定义步骤的输出
@dataclass
class StepOutcome:
    data: Any
    next_prompt: Optional[str] = None
    should_exit: bool = False
def try_call_generator(func, *args, **kwargs):
    """
    尝试调用函数，如果返回值是生成器则展开yield
    
    Args:
        func: 要调用的函数
        *args: 位置参数
        **kwargs: 关键字参数
    
    Returns:
        函数的返回值，如果是生成器则返回其最终返回值
    """
    ret = func(*args, **kwargs)
    if hasattr(ret, '__iter__') and not isinstance(ret, (str, bytes, dict, list)): ret = yield from ret
    return ret

class BaseHandler:
    def turn_end_callback(self, response, tool_calls, tool_results, turn, next_prompt, exit_reason):
        """
        回合结束回调函数，用于在每个交互回合结束时进行自定义处理
        
        Args:
            response: Agent的响应内容
            tool_calls: 工具调用列表
            tool_results: 工具执行结果列表
            turn: 当前回合数
            next_prompt: 下一轮的提示词
            exit_reason: 退出原因
        
        Returns:
            返回处理后的next_prompt，用于控制下一轮对话的提示词
        """
        return next_prompt
    # 分发工具调用 根据tool_name, 动态路由到对应的处理方法
    def dispatch(self, tool_name, args, response, index=0, tool_num=1):
        """
        分发工具调用到对应的处理方法
        
        根据tool_name动态路由到名为do_{tool_name}的方法进行执行。
        这是一个生成器方法，会yield出中间结果供调用方消费。
        
        Args:
            tool_name: 工具名称，用于构造方法名do_{tool_name}
            args: 工具执行参数字典
            response: Agent的原始响应内容
            index: 当前工具在批次中的索引位置
            tool_num: 当前批次中的工具总数
        
        Yields:
            工具执行过程中的中间输出
        
        Returns:
            StepOutcome对象，包含执行结果和下一轮提示词信息
        """
        method_name = f"do_{tool_name}"
        if hasattr(self, method_name):
            args['_index'] = index; args['_tool_num'] = tool_num
            _hook('tool_before', locals())
            ret = yield from try_call_generator(getattr(self, method_name), args, response)
            _hook('tool_after', locals())
            return ret
        elif tool_name == 'bad_json': return StepOutcome(None, next_prompt=args.get('msg', 'bad_json'), should_exit=False)
        else: 
            yield f"未知工具: {tool_name}\n"
            return StepOutcome(None, next_prompt=f"未知工具: {tool_name}", should_exit=False)

def json_default(o):
    """
    JSON序列化时的默认处理函数，用于处理未知类型
    
    Args:
        o: 无法序列化的对象
    
    Returns:
        set类型转为list，其他类型转为字符串
    """
    return list(o) if isinstance(o, set) else str(o)
def exhaust(g):
    """
    耗尽一个生成器并返回其最终返回值
    
    通过不断调用next()直到StopIteration异常来完全执行生成器，
    并捕获其return语句指定的值作为返回值。
    
    Args:
        g: 生成器对象
    
    Returns:
        生成器的return值（通过StopIteration.value获取）
    """
    try:
        while True: next(g)
    except StopIteration as e: return e.value

def get_pretty_json(data):
    """
    将数据格式化为美化的JSON字符串
    
    专门处理包含"script"字段的字典，将分号替换为带缩进的换行，
    使脚本内容更易读。
    
    Args:
        data: 要格式化的字典数据
    
    Returns:
        格式化后的JSON字符串，如果数据不是dict或不包含script字段则返回None
    """
    if isinstance(data, dict) and "script" in data:
        data = data.copy(); data["script"] = data["script"].replace(";", ";\n ")
        return json.dumps(data, indent=2, ensure_ascii=False).replace('\\n', '\n')

def agent_runner_loop(client, system_prompt, user_input, handler, tools_schema, 
                      max_turns=40, verbose=True, initial_user_content=None, yield_info=False):
    """
    Agent主运行循环，协调LLM、工具调用和对话流程
    
    Args:
        client: LLM客户端实例，用于发起聊天请求
        system_prompt: 系统提示词，定义Agent的行为角色
        user_input: 用户输入内容
        handler: 工具处理器，负责分发和执行工具调用
        tools_schema: 工具定义schema，描述可用工具及其参数
        max_turns: 最大运行回合数，默认40
        verbose: 是否输出详细过程信息，默认True
        initial_user_content: 初始用户内容，若为None则使用user_input
        yield_info: 是否yield回合信息，默认False
    
    Yields:
        过程中的状态信息和执行结果
    
    Returns:
        退出原因字典，包含result和data字段
    """
    message = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": initial_user_content if initial_user_content is not None else user_input}
    ]
    turn = 0; handler.max_turns = max_turns
    _hook('agent_before', locals())
    # 主循环：控制最大运行回合数
    while turn < handler.max_turns:
        turn += 1; turnstr = f'LLM Running (Turn {turn}) ...'
        # 根据是否有任务目录选择显示格式
        if handler.parent.task_dir: turnstr = f'Turn {turn} ...'
        if verbose: turnstr = f'**{turnstr}**'
        # 可选地yield回合基本信息
        if yield_info: yield {'turn': turn}
        yield f"\n{turnstr}\n\n"
        # 每10回合清空一次工具调用记录，防止上下文过长
        if turn%10 == 0: client.last_tools = ''
        _hook('turn_before', locals())
        _hook('llm_before', locals())
        # 调用LLM获取响应
        response_gen = client.chat(message = messages, tools=tools_schema)
        if verbose:
            response = yield from response_gen
            yield '\n\n'
        else:
            response = exhaust(response_gen)
            cleaned = _clean_content(response.content)
            if cleaned: yield cleaned + '\n'
        _hook('llm_after', locals())

        # 解析工具调用列表，若无工具调用则标记为no_tool
        if not response.tool_calls: tool_calls = [{'tool_name': 'no_tool', 'args': {}}]
        else: tool_calls = [{'tool_name': tc.function.name, 'args': json.loads(tc.function.arguments), 'id': tc.id}
                            for tc in response.tool_calls]

        tool_results = []; next_prompts = set(); exit_reason = {}
        # 遍历并执行每个工具调用
        for ii, tc in enumerate(tool_calls):
            tool_name, args, tid = tc['tool_name'], tc['args'], tc.get('id', '')
            if tool_name == 'no_tool': pass
            else: 
                if verbose: yield f"🛠️ Tool: `{tool_name}`  📥 args:\n````text\n{get_pretty_json(args)}\n````\n"
                else: yield f"🛠️ {tool_name}({_compact_tool_args(tool_name, args)})\n"
            handler.current_turn = turn
            # 分发工具调用到对应的处理方法
            gen = handler.dispatch(tool_name, args, response, index=ii, tool_num=len(tool_calls))
            try:
                v = next(gen)
                if verbose: yield '`````\n' + v
                outcome = (yield from gen) if verbose else exhaust(gen)
                if verbose: yield '`````\n'
            except StopIteration as e: outcome = e.value

            # 检查是否需要退出循环
            if outcome.should_exit:
                exit_reason = {'result': 'EXITED', 'data': outcome.data}; break
            if not outcome.next_prompt:
                exit_reason = {'result': 'CURRENT_TASK_DONE', 'data': outcome.data}; break
            # 遇到未知工具时清空工具缓存
            if outcome.next_prompt.startswith('未知工具'): client.last_tools = ''
            # 收集工具执行结果用于后续LLM上下文
            if outcome.data is not None and tool_name != 'no_tool':
                datastr = json.dumps(outcome.data, ensure_ascii=False, default=json_default) if type(outcome.data) in [dict, list] else str(outcome.data)
                tool_results.append({'tool_use_id': tid, 'content': datastr})
            next_prompts.add(outcome.next_prompt)
        # 判断是否需要结束循环
        if len(next_prompts) == 0 or exit_reason:
            # 若无更多提示且没有done_hooks则退出，否则使用下一个done_hook
            if len(handler._done_hooks) == 0 or exit_reason.get('result', '') == 'EXITED': break
            next_prompts.add(handler._done_hooks.pop(0))
        # 调用回合结束回调，获取下一轮提示词
        next_prompt = handler.turn_end_callback(response, tool_calls, tool_results, turn, '\n'.join(next_prompts), exit_reason)
        _hook('turn_after', locals())
        # 将工具结果作为新消息追加到对话历史
        messages.append({"role": "user", "content": next_prompt, "tool_results": tool_results})
    # 最终回合的回调处理
    if exit_reason: handler.turn_end_callback(response, tool_calls, tool_results, turn, '', exit_reason)
    _hook('agent_after', locals())
    return exit_reason or {'result': 'MAX_TURN_EXCEEDED'}

    
def _clean_content(text):
    """
    清理和压缩文本内容，移除冗余信息
    
    主要功能：
    1. 压缩过长的代码块（超过6行只显示前5行）
    2. 移除file_content、tool_use、tool_call等标签内容
    3. 合并多个连续空行
    
    Args:
        text: 待清理的原始文本
    
    Returns:
        清理后的文本
    """
    if not text: return ''
    # 内部函数：收缩代码块，对超过6行的代码块只显示前5行
    def _shrink_code(m):
        lines = m.group(0).split('\n')
        lang = lines[0].replace('```','').strip()
        # 获取代码体内容（排除首行语言标记和末尾的反引号行）
        body = [l for l in lines[1:-1] if l.strip()]
        # 代码行数不超过6行时保持原样
        if len(body) <= 6: return m.group(0)
        # 截取前5行作为预览
        preview = '\n'.join(body[:5])
        return f'```{lang}\n{preview}\n  ... ({len(body)} lines)\n```'
    # 替换所有代码块，应用收缩逻辑
    text = re.sub(r'```[\s\S]*?```', _shrink_code, text)
    # 移除冗余的XML标签内容，并合并多余空行
    for p in [r'<file_content>[\s\S]*?</file_content>', r'<tool_(?:use|call)>[\s\S]*?</tool_(?:use|call)>', r'(\r?\n){3,}']:
        text = re.sub(p, '\n\n' if '\\n' in p else '', text)
    return text.strip()

def _compact_tool_args(name, args):
    """
    压缩工具参数为紧凑的字符串表示
    
    用于在非verbose模式下显示工具调用的简短描述。
    特殊工具（update_working_checkpoint、ask_user）有专用格式化逻辑。
    
    Args:
        name: 工具名称
        args: 工具参数字典
    
    Returns:
        压缩后的参数字符串表示
    """
    # 过滤掉内部参数_index
    a = {k: v for k, v in args.items() if k != '_index'}
    # 对路径参数只保留文件名，缩短显示长度
    for k in ('path',): 
        if k in a: a[k] = os.path.basename(a[k])
    # update_working_checkpoint工具特殊处理：截断key_info字段
    if name == 'update_working_checkpoint': s = a.get('key_info', ''); return (s[:60]+'...') if len(s)>60 else s
    # ask_user工具特殊处理：格式化问题和候选选项
    if name == 'ask_user':
        q = str(a.get('question', ''))
        cs = a.get('candidates') or []
        if cs: q += '\ncandidates:\n' + '\n'.join(f'- {c}' for c in cs)
        return q
    # 其他工具：序列化为JSON，超长时截断
    s = json.dumps(a, ensure_ascii=False); return (s[:120]+'...') if len(s)>120 else s