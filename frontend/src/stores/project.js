import { defineStore } from 'pinia'
import {
  getProjects,
  getProject,
  createProject as apiCreateProject,
  updateProject as apiUpdateProject,
  deleteProject as apiDeleteProject
} from '@/api/project'

export const useProjectStore = defineStore('project', {
  state: () => ({
    projects: [],
    currentProject: null,
    loading: false
  }),

  actions: {
    async fetchProjects(params) {
      this.loading = true
      try {
        const data = await getProjects(params)
        this.projects = data.items || data || []
        return data
      } finally {
        this.loading = false
      }
    },

    async fetchProject(id) {
      this.loading = true
      try {
        const data = await getProject(id)
        this.currentProject = data
        return data
      } finally {
        this.loading = false
      }
    },

    async createProject(projectData) {
      const data = await apiCreateProject(projectData)
      this.projects.unshift(data)
      return data
    },

    async updateProject(id, projectData) {
      const data = await apiUpdateProject(id, projectData)
      const index = this.projects.findIndex((p) => p.id === id)
      if (index !== -1) {
        this.projects[index] = data
      }
      if (this.currentProject?.id === id) {
        this.currentProject = data
      }
      return data
    },

    async deleteProject(id) {
      await apiDeleteProject(id)
      this.projects = this.projects.filter((p) => p.id !== id)
      if (this.currentProject?.id === id) {
        this.currentProject = null
      }
    }
  }
})
