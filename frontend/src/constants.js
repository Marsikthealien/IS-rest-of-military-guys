// Ті самі значення, що в enum LeaveType / LeaveStatus на бекенді
export const LeaveType = {
  ANNUAL: 'щорічна основна',
  ADDITIONAL: 'додаткова',
  STUDY: 'навчальна',
  FAMILY: 'за сімейними обставинами',
  SICK: 'для лікування (через хворобу)',
}

export const LeaveStatus = {
  DRAFT: 'Чернетка',
  SUBMITTED: 'Подано',
  UNDER_REVIEW: 'На розгляді',
  APPROVED: 'Погоджено',
  REJECTED: 'Відхилено',
  SCHEDULED: 'Внесено до графіка',
  COMPLETED: 'Виконано',
  CANCELLED: 'Скасовано',
}

export const Roles = {
  SERVICE_MEMBER: 'Військовослужбовець',
  COMMANDER: 'Командир',
  HR_CLERK: 'Відповідальний за кадровий облік',
}

