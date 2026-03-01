<script setup>
import '@wangeditor/editor/dist/css/style.css'
import { onBeforeUnmount, ref, shallowRef, watch, computed } from 'vue'
import { Editor, Toolbar } from '@wangeditor/editor-for-vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: '',
  },
  height: {
    type: String,
    default: '300px',
  },
  mode: {
    type: String,
    default: 'default', // 'default' | 'simple'
  },
})

const emit = defineEmits(['update:modelValue'])

// 编辑器实例，必须用 shallowRef
const editorRef = shallowRef()

// 编辑器配置
const editorConfig = {
  placeholder: props.placeholder || t('common.editor.placeholder'),
  MENU_CONF: {
    // 上传图片时，自动转为 base64
    uploadImage: {
      customUpload(file, insertFn) {
        // 将图片读取为 base64 并插入
        const reader = new FileReader()
        reader.onload = (e) => {
          const base64 = e.target.result
          insertFn(base64, file.name, '')
        }
        reader.readAsDataURL(file)
      },
      // 允许粘贴图片
      allowedFileTypes: ['image/*'],
    },
  },
  // 自定义粘贴处理
  customPaste: (editor, event) => {
    // 获取剪贴板中的图片文件
    const clipboardData = event.clipboardData || window.clipboardData
    if (!clipboardData) return false
    
    const items = clipboardData.items
    if (!items) return false
    
    // 检查是否有图片文件
    for (let i = 0; i < items.length; i++) {
      const item = items[i]
      if (item.type.indexOf('image') !== -1) {
        const file = item.getAsFile()
        if (file) {
          // 阻止默认粘贴，手动处理图片
          event.preventDefault()
          const reader = new FileReader()
          reader.onload = (e) => {
            const base64 = e.target.result
            editor.dangerouslyInsertHtml(`<img src="${base64}" alt="pasted-image" />`)
          }
          reader.readAsDataURL(file)
          return true
        }
      }
    }
    
    // 如果没有图片文件，检查 HTML 内容中的图片
    const html = clipboardData.getData('text/html')
    if (html) {
      // 查找 HTML 中的图片标签，处理无效的 src
      const imgRegex = /<img[^>]*src=["']([^"']+)["'][^>]*>/gi
      let match
      let hasImage = false
      
      while ((match = imgRegex.exec(html)) !== null) {
        const src = match[1]
        // 检查是否是无效的图片源（如 cid: 引用、file: 协议、空 src）
        if (!src || src.startsWith('cid:') || src.startsWith('file:') || src.startsWith('blob:')) {
          hasImage = true
          break
        }
      }
      
      // 如果有无效图片引用，显示提示
      if (hasImage) {
        console.warn('粘贴内容包含无法加载的图片引用，建议通过截图方式粘贴图片')
      }
    }
    
    // 返回 false 表示使用默认粘贴行为
    return false
  },
}

// 工具栏配置
const toolbarConfig = computed(() => {
  if (props.mode === 'simple') {
    return {
      toolbarKeys: [
        'bold', 'italic', 'underline', 'through', '|',
        'color', 'bgColor', '|',
        'fontSize', 'fontFamily', '|',
        'bulletedList', 'numberedList', '|',
        'insertLink', 'insertTable', '|',
        'undo', 'redo',
      ],
    }
  }
  return {}
})

// 内容同步
const valueHtml = ref(props.modelValue || '')

watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal !== valueHtml.value) {
      valueHtml.value = newVal || ''
    }
  }
)

function handleChange(editor) {
  const html = editor.getHtml()
  emit('update:modelValue', html)
}

// 创建编辑器时记录实例
function handleCreated(editor) {
  editorRef.value = editor
}

// 组件销毁时，销毁编辑器
onBeforeUnmount(() => {
  const editor = editorRef.value
  if (editor != null) {
    editor.destroy()
  }
})
</script>

<template>
  <div class="rich-text-editor">
    <Toolbar
      class="editor-toolbar"
      :editor="editorRef"
      :defaultConfig="toolbarConfig"
      :mode="mode"
    />
    <Editor
      class="editor-content"
      :style="{ height }"
      v-model="valueHtml"
      :defaultConfig="editorConfig"
      :mode="mode"
      @onCreated="handleCreated"
      @onChange="handleChange"
    />
  </div>
</template>

<style scoped>
.rich-text-editor {
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  overflow: hidden;
}

.editor-toolbar {
  border-bottom: 1px solid #d9d9d9;
}

.editor-content {
  overflow-y: auto;
}

/* 使编辑器风格与 Naive UI 一致 */
:deep(.w-e-text-container) {
  background-color: #fff;
}

:deep(.w-e-text-placeholder) {
  color: #aaa;
  font-style: normal;
}
</style>
