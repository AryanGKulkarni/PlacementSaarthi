export const APP_NAME = 'PlacementSaarthi'

// Same ids as the departments seeded by the backend (DepartmentService.DEFAULT_DEPARTMENTS).
export const DEPARTMENTS = {
  1: { code: 'CSE', name: 'Computer Science & Engineering' },
  2: { code: 'IT', name: 'Information Technology' },
  3: { code: 'ENTC', name: 'Electronics & Telecommunication' },
  4: { code: 'MECH', name: 'Mechanical Engineering' },
  5: { code: 'CIVIL', name: 'Civil Engineering' },
}

// Values match the backend Designation enum.
export const DESIGNATIONS = [
  ['assistant_professor', 'Assistant Professor'],
  ['associate_professor', 'Associate Professor'],
  ['professor', 'Professor'],
  ['hod', 'Head of Department (HOD)'],
  ['tpo', 'Training & Placement Officer (TPO)'],
]

export const ROLE_LABELS = {
  student: 'Student',
  faculty: 'Faculty',
  admin: 'Admin',
}

// Badge tone for the readiness level returned by the backend.
export const LEVEL_TONE = {
  Ready: 'green',
  'Almost ready': 'amber',
  'Needs work': 'red',
}
